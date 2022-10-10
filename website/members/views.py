import datetime
import logging
import time
import uuid
from urllib import parse

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Max
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.views import View
from django.views.generic import TemplateView, CreateView, ListView, DetailView

from members import logic, utils
from members.constants import DEFAULT_PAGINATION
from events.helpers.views import search_filtered_queryset
from members.forms import SignupPersonForm, SignupOrganizationForm
from members.models import Person, Organization, Category, Member, Quota, Payment

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
    template_name = 'members/signup_person_form.html'
    success_url = reverse_lazy('signup_person_thankyou')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        human_cats = Category.HUMAN_CATEGORIES
        context["categories"] = Category.objects.order_by('-fee').filter(name__in=human_cats)
        return context

    def form_invalid(self, form):
        messages.error(self.request, _("Por favor, revise los campos."))
        return super().form_invalid(form)

    def form_valid(self, form):
        response = super().form_valid(form)
        error_code = str(uuid.uuid4())
        try:
            utils.send_missing_info_mail(form.instance.membership)
        except Exception as err:
            logger.exception(
                "Problems sending post-registration email [%s] to member %s: %r",
                error_code, form.instance.membership, err)
            msg = (
                "No pudimos enviarte el email para continuar con el proceso de registración, "
                "por favor mandanos un mail a presidencia@ac.python.org.ar indicando "
                "el código de error {}. ¡Gracias!".format(error_code))
            messages.warning(self.request, _(msg))

        return response


class SignupOrganizationsFormView(CreateView):
    form_class = SignupOrganizationForm
    model = Organization
    template_name = 'members/signup_org_form.html'
    success_url = reverse_lazy('signup_organization_thankyou')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        human_cats = Category.HUMAN_CATEGORIES
        context["categories"] = [
            {
                'name': cat.name,
                'description': cat.description,
                'anual_fee': cat.fee * 12,
            } for cat in Category.objects.order_by('-fee').exclude(name__in=human_cats)]
        return context


class SignupPersonThankyouView(TemplateView):
    template_name = 'members/signup_person_thankyou.html'


class SignupOrganizationThankyouView(TemplateView):
    template_name = 'members/signup_organization_thankyou.html'


class ReportsInitialView(OnlyAdminsViewMixin, TemplateView):
    template_name = 'members/reports_main.html'


class ReportDebts(OnlyAdminsViewMixin, View):
    """Handle the report about debts."""
    MAIL_SUBJECT = "Cuotas adeudadas a la Asociación Civil Python Argentina"

    def post(self, request):
        raw_sendmail = parse.parse_qs(request.body)[b'sendmail']
        to_send_mail_ids = map(int, raw_sendmail)
        limit_year, limit_month = self._get_yearmonth(request)

        sent_error = 0
        sent_ok = 0
        tini = time.time()
        errors_code = str(uuid.uuid4())
        for member_id in to_send_mail_ids:
            member = Member.objects.get(id=member_id)

            debt = logic.get_debt_state(member, limit_year, limit_month)
            debt_info = {
                'debt': utils.build_debt_string(debt),
                'member': member,
                'annual_fee': member.category.fee * 12,
                'on_purpose_missing_var': "ERROR",
            }
            text = render_to_string('members/mail_indebt.txt', debt_info)
            if 'ERROR' in text:
                # badly built template
                logger.error(
                    "Error when building the report missing mail result, info: %s", debt_info)
                return HttpResponse("Error al armar la página")
            try:
                utils.send_email(member, self.MAIL_SUBJECT, text)
            except Exception as err:
                sent_error += 1
                logger.exception(
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

    def _get_yearmonth(self, request):
        try:
            year = int(request.GET['limit_year'])
            month = int(request.GET['limit_month'])
        except (KeyError, ValueError):
            # get by default one month before now, as it's the first month not really
            # paid (current month is not yet finished)
            currently = now()
            year, month = logic.decrement_year_month(currently.year, currently.month)
        return year, month

    def get(self, request):
        """Produce the report with the given year/month limits."""
        limit_year, limit_month = self._get_yearmonth(request)

        # get those already confirmed members
        members = Member.objects\
            .filter(legal_id__isnull=False, category__fee__gt=0, shutdown_date__isnull=True)\
            .order_by('legal_id').all()

        debts = []
        for member in members:
            debt = logic.get_debt_state(member, limit_year, limit_month)
            if debt:
                debts.append({
                    'member': member,
                    'debt': utils.build_debt_string(debt),
                })

        context = {
            'debts': debts,
            'limit_year': limit_year,
            'limit_month': limit_month,
        }
        return render(request, 'members/report_debts.html', context)


class ReportMissing(OnlyAdminsViewMixin, View):
    """Handle the report about what different people miss to get approved as a member."""
    MAIL_SUBJECT = "Continuación del trámite de inscripción a la Asociación Civil Python Argentina"

    def post(self, request):
        raw_sendmail = parse.parse_qs(request.body)[b'sendmail']
        to_send_mail_ids = map(int, raw_sendmail)
        sent_error = 0
        sent_ok = 0
        tini = time.time()
        errors_code = str(uuid.uuid4())
        for member_id in to_send_mail_ids:
            member = Member.objects.get(id=member_id)
            try:
                utils.send_missing_info_mail(member)
            except Exception as err:
                sent_error += 1
                logger.exception(
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
        not_yet_members = Member.objects.filter(
            legal_id=None, shutdown_date=None).order_by('created').all()

        incompletes = []
        for member in not_yet_members:
            missing_info = member.get_missing_info()

            # convert missing info to proper strings to show
            for k, v in missing_info.items():
                missing_info[k] = "FALTA" if v else ""

            # add member and store
            missing_info['member'] = member
            incompletes.append(missing_info)

        context = dict(incompletes=incompletes)
        return render(request, 'members/report_missing.html', context)


class ReportComplete(View):
    """Handles the report on people who are in a position to be approved as members"""

    MAIL_SUBJECT = "Continuación del trámite de inscripción a la Asociación Civil Python Argentina"
    MAIL_MANAGER = 'presidencia@ac.python.org.ar'

    def post(self, request):
        to_approve_ids = map(int, request.POST.getlist('approve'))
        registration_date = datetime.datetime.strptime(
            request.POST['registration_date'], '%Y-%m-%d')

        sent_error = 0
        sent_ok = 0
        tini = time.time()
        errors_code = str(uuid.uuid4())

        # get the first free legal id
        _max_legal_id_query = Member.objects.aggregate(Max('legal_id'))
        next_legal_id = _max_legal_id_query['legal_id__max'] + 1

        for member_id in to_approve_ids:
            member = Member.objects.get(id=member_id)

            # approve the member, setting a new legal_id and date to it
            member.legal_id = next_legal_id
            member.registration_date = registration_date
            member.save()
            next_legal_id += 1

            # send a mail to the person informing new membership
            info = {
                'member_type': member.category.name,
                'member_number': member.legal_id,
            }
            text = render_to_string('members/mail_newmember.txt', info)
            try:
                utils.send_email(member, self.MAIL_SUBJECT, text, cc=[self.MAIL_MANAGER])
            except Exception as err:
                sent_error += 1
                logger.exception(
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

        completes = []
        for member in not_yet_members:
            anything_missing = any(member.get_missing_info(for_approval=True).values())
            if anything_missing:
                continue

            person = member.person
            person_info = {
                'nombre': person.first_name,
                'apellido': person.last_name,
                'dni': person.document_number,
                'email': person.email,
                'member': member,
            }
            completes.append(person_info)

        context = dict(completes=completes)
        return render(request, 'members/report_complete.html', context)


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
                    Q(first_payment_year__lt=year)
                    | Q(first_payment_year=year, first_payment_month__lte=month)
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


class MembersListView(LoginRequiredMixin, ListView):
    model = Member
    context_object_name = 'members_list'
    template_name = 'members/members_list.html'
    paginate_by = DEFAULT_PAGINATION
    search_fields = {
        'person__first_name': 'icontains',
        'person__last_name': 'icontains',
        'person__email': 'icontains',
        'person__document_number': 'icontains',
        'organization__name': 'icontains',
        'organization__document_number': 'icontains'
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        search_value = self.request.GET.get('search', None)
        if search_value and search_value != '':
            queryset = search_filtered_queryset(queryset, self.search_fields, search_value)
        return queryset

    def get(self, request, *args, **kwargs):
        """
            If get one result when call self.get_queryset() then
            redirect to member_detail view, else display the filtered
            list of members
        """
        if self.get_queryset().count() == 1:
            return redirect('member_detail', self.get_queryset().first().pk)
        return super().get(request, *args, **kwargs)


class MemberDetailView(LoginRequiredMixin, DetailView):
    model = Member
    template_name = 'members/member_detail.html'

    def _get_last_payments(self, member):
        """Get the info for last payments."""
        quotas = Quota.objects.filter(member=member).all()
        grouped = {}
        for q in quotas:
            grouped.setdefault(q.payment, []).append(q)

        payments = sorted(grouped.items(), key=lambda pq: pq[0].timestamp, reverse=True)
        info = []
        for payment, quotas in payments:
            if payment.invoice_ok:
                invoice = '{}-{}'.format(payment.invoice_spoint, payment.invoice_number)
            else:
                invoice = '(-)'
            info.append({
                'title': "{} x {:.2f}".format(payment.strategy.platform.title(), payment.amount),
                'timestamp': payment.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'invoice': invoice,
                'quotas': ', '.join(sorted(q.code for q in quotas)),
            })

        return info

    def get_context_data(self, **kwargs):
        # Get the context from base
        context = super().get_context_data(**kwargs)
        member = self.get_object()
        today = datetime.date.today()
        debt = logic.get_debt_state(member, today.year, today.month)
        if len(debt) > 1 and member.category.fee > 0:
            context['debtor'] = True
        context['member'] = member
        context['last_payments_info'] = self._get_last_payments(member)
        context['missing_letter'] = not member.has_subscription_letter
        return context


# public
signup_initial = SignupInitialView.as_view()
signup_form_person = SignupPersonFormView.as_view()
signup_form_organization = SignupOrganizationsFormView.as_view()
signup_person_thankyou = SignupPersonThankyouView.as_view()
signup_organization_thankyou = SignupOrganizationThankyouView.as_view()
# only admins
reports_main = ReportsInitialView.as_view()
report_debts = ReportDebts.as_view()
report_missing = ReportMissing.as_view()
report_complete = ReportComplete.as_view()
report_income_quotas = ReportIncomeQuotas.as_view()
report_income_money = ReportIncomeMoney.as_view()
members_list = MembersListView.as_view()
member_detail = MemberDetailView.as_view()
