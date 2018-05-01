from django.contrib import messages
from django.urls import reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.translation import ugettext as _
from django.shortcuts import render
from django.views.generic import TemplateView, CreateView
from members.models import Person, Organization, Category
from members.forms import SignupPersonForm


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
    fields = '__all__'
    model = Organization
    template_name = 'members/signup_form.html'


class SignupThankyouView(TemplateView):
    template_name = 'members/signup_thankyou.html'


signup_initial = SignupInitialView.as_view()
signup_form_person = SignupPersonFormView.as_view()
signup_form_organization = SignupOrganizationsFormView.as_view()
signup_thankyou = SignupThankyouView.as_view()
