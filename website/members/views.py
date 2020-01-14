import datetime
import logging
import re
import os
import time
import uuid
from urllib import parse

import certg
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.mail import EmailMessage
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.views import View
from django.views.generic import TemplateView, CreateView, ListView, DetailView

import members
from members import logic
from members.constants import (
    DEFAULT_PAGINATION,
)
from events.helpers.views import search_filtered_queryset
from members.forms import SignupPersonForm, SignupOrganizationForm
from members.models import Person, Organization, Category, Member, Quota, Payment

logger = logging.getLogger(__name__)


def _clean_double_empty_lines(oldtext):
    while True:
        newtext = re.sub("\n *?\n *?\n", "\n\n", oldtext)
        if newtext == oldtext:
            return newtext
        oldtext = newtext


def _build_debt_string(debt):
    """Build a nice string to represent the debt."""
    if not debt:
        return "-"

    # convert tuples to nice string format (only first 3, the used ones)
    debt_nicer = ["{}-{:02d}".format(*d) for d in debt[:3]]
    exceeding = "" if len(debt) <= 3 else ", ..."
    result = "{} ({}{})".format(len(debt), ", ".join(debt_nicer), exceeding)
    return result


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
    success_url = reverse_lazy('signup_thankyou')

    def get_context_data(self, **kwargs):
        context = super(SignupPersonFormView, self).get_context_data(**kwargs)
        context["categories"] = Category.objects.order_by('-fee')
        return context

    def form_invalid(self, form):
        messages.error(self.request, _("Por favor, revise los campos."))
        return super(SignupPersonFormView, self).form_invalid(form)


class SignupOrganizationsFormView(CreateView):
    form_class = SignupOrganizationForm
    model = Organization
    template_name = 'members/signup_org_form.html'
    success_url = reverse_lazy('signup_thankyou')


class SignupThankyouView(TemplateView):
    template_name = 'members/signup_thankyou.html'


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
                'debt': _build_debt_string(debt),
                'member': member,
                'annual_fee': member.category.fee * 12,
                'on_purpose_missing_var': "ERROR",
            }
            text = render_to_string('members/mail_indebt.txt', debt_info)
            text = _clean_double_empty_lines(text)
            if 'ERROR' in text:
                # badly built template
                logger.error(
                    "Error when building the report missing mail result, info: %s", debt_info)
                return HttpResponse("Error al armar la página")
            recipient = f"{member.entity.full_name} <{member.entity.email}>"
            mail = EmailMessage(self.MAIL_SUBJECT, text, settings.EMAIL_FROM, [recipient])
            try:
                mail.send()
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

    def _get_yearmonth(self, request):
        try:
            year = int(request.GET['limit_year'])
            month = int(request.GET['limit_month'])
        except (KeyError, ValueError):
            # get by default one month before now, as it's the first month not really
            # paid (current month is not yet finished)
            currently = now()
            year = currently.year
            month = currently.month - 1
            if month <= 0:
                year -= 1
                month += 12
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
                    'debt': _build_debt_string(debt),
                })

        context = {
            'debts': debts,
            'limit_year': limit_year,
            'limit_month': limit_month,
        }
        return render(request, 'members/report_debts.html', context)


def get_member_missing_info(member):
    """Analyze and indicate in which categories the member is missing somethhing."""
    cat_student = Category.objects.get(name=Category.STUDENT)
    cat_collab = Category.objects.get(name=Category.COLLABORATOR)

    # simple flags with "Not Applicable" situation
    missing_student_certif = (
        member.category == cat_student and not member.has_student_certificate)
    missing_collab_accept = (
        member.category == cat_collab and not member.has_collaborator_acceptance)

    # info from Person
    missing_nickname = member.person.nickname == ""
    # picture is complicated, bool() is used to check if the Image field has an associated
    # filename, and False itself is used as the "dont want a picture!" flag
    missing_picture = not member.person.picture and member.person.picture is not False

    # info from Member itself
    missing_payment = member.first_payment_month is None and member.category.fee > 0
    missing_signed_letter = not member.has_subscription_letter

    return {
        'missing_signed_letter': missing_signed_letter,
        'missing_student_certif': missing_student_certif,
        'missing_payment': missing_payment,
        'missing_nickname': missing_nickname,
        'missing_picture': missing_picture,
        'missing_collab_accept': missing_collab_accept,
    }


class ReportMissing(OnlyAdminsViewMixin, View):
    """Handle the report about what different people miss to get approved as a member."""
    MAIL_SUBJECT = "Continuación del trámite de inscripción a la Asociación Civil Python Argentina"

    def _generate_letter(self, member):
        """Generate the letter to be signed."""
        letter_svg_template = os.path.join(
            os.path.dirname(members.__file__), 'templates', 'members', 'carta.svg')
        path_prefix = "/tmp/letter"
        person = member.person
        person_info = {
            'tiposocie': member.category.name,
            'nombre': person.first_name,
            'apellido': person.last_name,
            'dni': person.document_number,
            'email': person.email,
            'nacionalidad': person.nationality,
            'estadocivil': person.marital_status,
            'profesion': person.occupation,
            'fechanacimiento': person.birth_date.strftime("%Y-%m-%d"),
            'domicilio': person.street_address,
            'ciudad': person.city,
            'codpostal': person.zip_code,
            'provincia': person.province,
            'pais': person.country,
        }

        # this could be optimized to generate all PDFs at once, but we're fine so far
        (letter_filepath,) = certg.process(
            letter_svg_template, path_prefix, "dni", [person_info], images=None)
        return letter_filepath

    def _analyze_member(self, member):
        """Analyze and indicate in which categories the member is missing somethhing."""
        return get_member_missing_info(member)

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
            missing_info = self._analyze_member(member)
            missing_info['annual_fee'] = member.category.fee * 12
            missing_info['member'] = member
            missing_info['on_purpose_missing_var'] = "ERROR"
            text = render_to_string('members/mail_missing.txt', missing_info)
            text = _clean_double_empty_lines(text)
            if 'ERROR' in text:
                # badly built template
                logger.error(
                    "Error when building the report missing mail result, info: %s", missing_info)
                return HttpResponse("Error al armar la página")

            # if missing the signed letter, produce it and attach it
            if missing_info['missing_signed_letter']:
                letter_filepath = self._generate_letter(member)

            # build the mail
            recipient = f"{member.entity.full_name} <{member.entity.email}>"
            mail = EmailMessage(self.MAIL_SUBJECT, text, settings.EMAIL_FROM, [recipient])
            if missing_info['missing_signed_letter']:
                mail.attach_file(letter_filepath)

            # actually send it
            try:
                mail.send()
            except Exception as err:
                sent_error += 1
                logger.error(
                    "Problems sending email [%s] to member %s: %r", errors_code, member, err)
            else:
                sent_ok += 1
            finally:
                if missing_info['missing_signed_letter']:
                    try:
                        os.unlink(letter_filepath)
                    except Exception as exc:
                        logger.warning("Couldn't remove letter file %r: %r", letter_filepath, exc)

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
            missing_info = self._analyze_member(member)

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
    MAIL_FROM = 'Lalita <lalita@ac.python.org.ar>'
    MAIL_MANAGER = 'presidencia@ac.python.org.ar>'

    def post(self, request):
        print("======body?", parse.parse_qs(request.body))
        raw_approve = parse.parse_qs(request.body)[b'approve']
        to_approve_ids = map(int, raw_approve)
        sent_error = 0
        sent_ok = 0
        tini = time.time()
        errors_code = str(uuid.uuid4())
        for member_id in to_approve_ids:
            member = Member.objects.get(id=member_id)

            # approve the member, setting a new legal_id to it
            print("======= FIXME: approve", member)

            # send a mail to the person informing new membership
            print("======= FIXME: send mail about new membership")
            # text = render_to_string('members/mail_missing.txt', missing_info)
            # text = _clean_double_empty_lines(text)
            # if 'ERROR' in text:
            #     # badly built template
            #     logger.error(
            #         "Error when building the report missing mail result, info: %s", missing_info)
            #     return HttpResponse("Error al armar la página")

            # # build the mail
            # recipient = f"{member.entity.full_name} <{member.entity.email}>"
            # mail = EmailMessage(
            #     self.MAIL_SUBJECT, text, self.MAIL_FROM, [recipient],
            #     cc=[self.MAIL_MANAGER], reply_to=[self.MAIL_MANAGER])
            # if missing_info['missing_signed_letter']:
            #     mail.attach_file(letter_filepath)

            # # actually send it
            # try:
            #     mail.send()
            # except Exception as err:
            #     sent_error += 1
            #     logger.error(
            #         "Problems sending email [%s] to member %s: %r", errors_code, member, err)
            # else:
            #     sent_ok += 1
            # finally:
            #     if missing_info['missing_signed_letter']:
            #         try:
            #             os.unlink(letter_filepath)
            #         except Exception as exc:
            #            logger.warning("Couldn't remove letter file %r: %r", letter_filepath, exc)

        deltat = time.time() - tini
        context = {
            'sent_ok': sent_ok,
            'sent_error': sent_error,
            'errors_code': errors_code,
            'deltamsec': int(deltat * 1000),
        }
        return render(request, 'members/mail_sent.html', context)

    def _analyze_member(self, member):
        """Analyze and indicate in which categories the member is missing somethhing."""
        missing_info = get_member_missing_info(member)
        anything_missing = any(missing_info.values())
        return anything_missing

    def get(self, request):
        not_yet_members = Member.objects.filter(legal_id=None).order_by('created').all()

        completes = []
        for member in not_yet_members:
            anything_missing = self._analyze_member(member)
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
        queryset = super(MembersListView, self).get_queryset()
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

    def get_context_data(self, **kwargs):
        # Get the context from base
        context = super(MemberDetailView, self).get_context_data(**kwargs)
        member = self.get_object()
        today = datetime.date.today()
        debt = logic.get_debt_state(member, today.year, today.month)
        if len(debt) > 1 and member.category.fee > 0:
            context['debtor'] = True
        context['member'] = member
        context['quotas'] = Quota.objects.filter(member=member)[:6]
        context['missing_letter'] = not member.has_subscription_letter
        return context


# public
signup_initial = SignupInitialView.as_view()
signup_form_person = SignupPersonFormView.as_view()
signup_form_organization = SignupOrganizationsFormView.as_view()
signup_thankyou = SignupThankyouView.as_view()
# only admins
reports_main = ReportsInitialView.as_view()
report_debts = ReportDebts.as_view()
report_missing = ReportMissing.as_view()
report_complete = ReportComplete.as_view()
report_income_quotas = ReportIncomeQuotas.as_view()
report_income_money = ReportIncomeMoney.as_view()
members_list = MembersListView.as_view()
member_detail = MemberDetailView.as_view()
