from django.contrib import messages
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.utils.translation import ugettext as _
from django.views import View
from django.views.generic import TemplateView, CreateView

from members import logic
from members.forms import SignupPersonForm, SignupOrganizationForm
from members.models import Person, Organization, Category, Member


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

    def _produce_report(self, request, limit_year, limit_month):
        """Produce the report with the given year/month limits."""
        # get those already confirmed members
        members = Member.objects.filter(legal_id__isnull=False, category__fee__gt=0).all()

        debts = []
        for member in members:
            in_debt, last_quota = logic.get_debt_state(member, limit_year, limit_month)
            if in_debt:
                last_payment = "-" if last_quota is None else last_quota.code
                debts.append({
                    'member': member,
                    'last_payment': last_payment,
                })

        context = {
            'debts': debts,
            'limit_year': limit_year,
            'limit_month': limit_month,
        }
        return render(request, 'members/report_debts.html', context)

    def get(self, request):
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

        return self._produce_report(request, year, month)


signup_initial = SignupInitialView.as_view()
signup_form_person = SignupPersonFormView.as_view()
signup_form_organization = SignupOrganizationsFormView.as_view()
signup_thankyou = SignupThankyouView.as_view()
reports_main = ReportsInitialView.as_view()
report_debts = ReportDebts.as_view()
