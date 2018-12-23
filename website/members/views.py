import logging
import re
import time
import uuid
from urllib import parse

from django.contrib import messages
from django.core.mail import EmailMessage
from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.views import View
from django.views.generic import TemplateView, CreateView

from members import logic
from members.forms import SignupPersonForm, SignupOrganizationForm
from members.models import Person, Organization, Category, Member

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


class ReportsInitialView(TemplateView):
    template_name = 'members/reports_main.html'


class ReportDebts(View):
    """Handle the report about debts."""

    MAIL_SUBJECT = "Cuotas adeudadas a la Asociación Civil Python Argentina"
    MAIL_FROM = 'Lalita <lalita@ac.python.org.ar>'
    MAIL_MANAGER = 'presidencia@ac.python.org.ar>'

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
            msg = EmailMessage(
                self.MAIL_SUBJECT, text, self.MAIL_FROM, [recipient],
                cc=[self.MAIL_MANAGER], reply_to=[self.MAIL_MANAGER])
            try:
                msg.send()
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
            # get by default two months before now, as users would be ok until paying that month
            # inclusive, as the last month is the first month not really paid (current month is
            # not yet finished)
            currently = now()
            year = currently.year
            month = currently.month - 2
            if month <= 0:
                year -= 1
                month += 12
        return year, month

    def get(self, request):
        """Produce the report with the given year/month limits."""
        limit_year, limit_month = self._get_yearmonth(request)

        # get those already confirmed members
        members = Member.objects\
            .filter(legal_id__isnull=False, category__fee__gt=0)\
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


class ReportMissing(View):
    """Handle the report about what different people miss to get approved as a member."""

    MAIL_SUBJECT = "Continuación del trámite de inscripción a la Asociación Civil Python Argentina"
    MAIL_FROM = 'Lalita <lalita@ac.python.org.ar>'
    MAIL_MANAGER = 'presidencia@ac.python.org.ar>'

    def post(self, request):
        raw_sendmail = parse.parse_qs(request.body)[b'sendmail']
        to_send_mail_ids = map(int, raw_sendmail)
        sent_error = 0
        sent_ok = 0
        tini = time.time()
        errors_code = str(uuid.uuid4())
        for member_id in to_send_mail_ids:
            member = Member.objects.get(id=member_id)
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
            recipient = f"{member.entity.full_name} <{member.entity.email}>"
            msg = EmailMessage(
                self.MAIL_SUBJECT, text, self.MAIL_FROM, [recipient],
                cc=[self.MAIL_MANAGER], reply_to=[self.MAIL_MANAGER])
            try:
                msg.send()
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

    def _analyze_member(self, member):
        """Analyze and indicate in which categories the member is missing somethhing."""
        cat_student = Category.objects.get(name=Category.STUDENT)
        cat_collab = Category.objects.get(name=Category.COLLABORATOR)

        # simple flags with "Not Applicable" situation
        missing_student_certif = (
            member.category == cat_student and not member.has_student_certificate)
        missing_collab_accept = (
            member.category == cat_collab and not member.has_collaborator_acceptance)

        # info from Person
        missing_nickname = member.person.nickname is None
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

    def get(self, request):
        not_yet_members = Member.objects.filter(legal_id=None).order_by('created').all()

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


signup_initial = SignupInitialView.as_view()
signup_form_person = SignupPersonFormView.as_view()
signup_form_organization = SignupOrganizationsFormView.as_view()
signup_thankyou = SignupThankyouView.as_view()
reports_main = ReportsInitialView.as_view()
report_debts = ReportDebts.as_view()
report_missing = ReportMissing.as_view()
