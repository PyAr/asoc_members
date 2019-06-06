import datetime
import logging
import time
import uuid
from urllib import parse

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.translation import ugettext as _
from django.views import View
from django.views.generic import TemplateView, CreateView, DetailView

from members import logic
from members.forms import SignupPersonForm, SignupOrganizationForm
from members.models import Person, Organization, Category, Member, Quota, Payment
from members.utils import (
    sendmail_missing_info, sendmail_about_debts,
    build_debt_string, get_yearmonth)


logger = logging.getLogger(__name__)


class OnlyAdminsViewMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)


class SignupInitialView(TemplateView):
    template_name = 'members/signup_initial.html'


class SignupPersonFormView(CreateView):
    model = Person
    form_class = SignupPersonForm
    template_name = 'members/signup_form.html'

    def get_context_data(self, **kwargs):
        context = super(SignupPersonFormView, self).get_context_data(**kwargs)
        context["categories"] = Category.objects.order_by('-fee')
        return context

    def form_invalid(self, form):
        messages.error(self.request, _("Por favor, revise los campos."))
        return super(SignupPersonFormView, self).form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        try:
            sendmail_missing_info(form.instance.membership)
        except ConnectionError:
            messages.warning(
                self.request, _(
                    "No pudimos enviarte el email con la carta de afiliación."
                    " Puedes descargarla más abajo"))
        return response

    def get_success_url(self):
        return reverse_lazy('signup_person_thankyou', args=(self.object.membership_id, ))


class SignupOrganizationsFormView(CreateView):
    form_class = SignupOrganizationForm
    model = Organization
    template_name = 'members/signup_org_form.html'
    success_url = reverse_lazy('signup_organization_thankyou')


class SignupThankyouView(DetailView):
    model = Member
    template_name = 'members/signup_person_thankyou.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(ctx["object"]._analyze())
        return ctx


class SignupOrganizationThankyouView(TemplateView):
    template_name = 'members/signup_organization_thankyou.html'


class ReportsInitialView(OnlyAdminsViewMixin, TemplateView):
    template_name = 'members/reports_main.html'


class ReportDebts(OnlyAdminsViewMixin, View):
    """Handle the report about debts."""

    def post(self, request):
        raw_sendmail = parse.parse_qs(request.body)[b'sendmail']
        to_send_mail_ids = map(int, raw_sendmail)
        limit_year, limit_month = get_yearmonth(request)
        sent_error = 0
        sent_ok = 0
        tini = time.time()
        errors_code = str(uuid.uuid4())
        for member_id in to_send_mail_ids:
            member = Member.objects.get(id=member_id)
            try:
                sendmail_about_debts(member, limit_year, limit_month)
            except Exception as exc:
                sent_error += 1
                logger.error(
                    "Problems sending email [%s] to member %s: %r", errors_code, member, exc)
            else:
                sent_ok += 1
        deltat = time.time() - tini

        context = {
            'sent_ok': sent_ok,
            'sent_error': sent_error,
            'errors_code': errors_code,
            'deltamsec': int(deltat * 1000),
        }
        return render(request, 'members/mail_sent.html', context)

    def get(self, request):
        """Produce the report with the given year/month limits."""
        limit_year, limit_month = get_yearmonth(request)

        # get those already confirmed members
        members = Member.objects.filter(
            legal_id__isnull=False, category__fee__gt=0,
            shutdown_date__isnull=True).order_by('legal_id').all()

        debts = []
        for member in members:
            debt = logic.get_debt_state(member, limit_year, limit_month)
            if debt:
                debts.append({
                    'member': member,
                    'debt': build_debt_string(debt),
                })

        context = {
            'debts': debts,
            'limit_year': limit_year,
            'limit_month': limit_month,
        }
        return render(request, 'members/report_debts.html', context)


class ReportMissing(OnlyAdminsViewMixin, View):
    """Handle the report about what different people miss to get approved as a member."""

    def post(self, request):
        raw_sendmail = parse.parse_qs(request.body)[b'sendmail']
        to_send_mail_ids = map(int, raw_sendmail)
        sent_error = 0
        sent_ok = 0
        tini = time.time()
        errors_code = str(uuid.uuid4())
        for member_id in to_send_mail_ids:
            member = Member.objects.get(id=member_id)

            # create the mail text from the template
            try:
                sendmail_missing_info(member)
            except Exception as err:
                sent_error += 1
                logger.error(
                    "Problems sending email [%s] to member %s: %r", errors_code, member, err)
            else:
                sent_ok += 1

        deltat = time.time() - tini
        context = {
            'sent_ok': sent_ok,
            'sent_error': sent_error,
            'errors_code': errors_code,
            'deltamsec': int(deltat * 1000),
        }
        return render(request, 'members/mail_sent.html', context)

    def get(self, request):
        not_yet_members = Member.objects.filter(legal_id=None).order_by('created').all()

        incompletes = []
        for member in not_yet_members:
            missing_info = member._analyze()

            # convert missing info to proper strings to show
            for k, v in missing_info.items():
                missing_info[k] = "FALTA" if v else ""

            # add member and store
            missing_info['member'] = member
            incompletes.append(missing_info)

        context = dict(incompletes=incompletes)
        return render(request, 'members/report_missing.html', context)


class ReportIncomeQuotas(OnlyAdminsViewMixin, View):
    """Handle the report showing income per quotas."""

    def get(self, request):
        # months for last two years
        today = datetime.date.today()
        yearmonths = reversed(list(logic.get_year_month_range(today.year - 2, today.month, 24)))

        # categories with non-zero fees
        categs = Category.objects.filter(fee__gt=0).all()
        categs_names = [c.name for c in categs]

        info_per_month = []
        for year, month in yearmonths:
            info = dict(year=year, month=month, members_info=[], total=0, real=0)
            info_per_month.append(info)

            for categ in categs:
                # "active" as in members that already started to pay and didn't shutdown (no
                # matter when they got the legal_id, really)
                active_members = Member.objects.filter(
                    first_payment_month__isnull=False,
                    shutdown_date__isnull=True,
                    category=categ,
                ).filter(
                    Q(first_payment_year__lt=year) |
                    Q(first_payment_year=year, first_payment_month__lte=month)
                ).all()

                # get how many quotas exist for those members for the given year/month
                quotas = Quota.objects.filter(
                    year=year, month=month, member__in=active_members).all()

                member_info = dict(total=len(active_members), paid=len(quotas))
                info['members_info'].append(member_info)

                info['total'] += len(active_members) * categ.fee
                info['real'] += len(quotas) * categ.fee

        context = dict(info_per_month=info_per_month, categories=categs_names)
        return render(request, 'members/report_income_quotas.html', context)


class ReportIncomeMoney(OnlyAdminsViewMixin, View):
    """Handle the report showing income per quotas."""

    def get(self, request):
        # months for last two years
        today = datetime.date.today()
        yearmonths = reversed(list(logic.get_year_month_range(today.year - 2, today.month, 24)))

        info_per_month = []
        for year, month in yearmonths:
            payments = Payment.objects.filter(
                timestamp__year=year, timestamp__month=month).aggregate(Sum('amount'))
            amount = payments['amount__sum'] or '-'
            info_per_month.append(dict(year=year, month=month, amount=amount))

        context = dict(info_per_month=info_per_month)
        return render(request, 'members/report_income_money.html', context)


# public
signup_initial = SignupInitialView.as_view()
signup_form_person = SignupPersonFormView.as_view()
signup_form_organization = SignupOrganizationsFormView.as_view()
signup_thankyou = SignupThankyouView.as_view()
signup_organization_thankyou = SignupOrganizationThankyouView.as_view()
# only admins
reports_main = ReportsInitialView.as_view()
report_debts = ReportDebts.as_view()
report_missing = ReportMissing.as_view()
report_income_quotas = ReportIncomeQuotas.as_view()
report_income_money = ReportIncomeMoney.as_view()
