import datetime
import logging
import time
import uuid
from urllib import parse

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum, Max
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.utils.timezone import now
from django.utils.translation import gettext as _
from django.views import View
from django.views.generic import TemplateView, CreateView, ListView, DetailView
from django.core.paginator import Paginator

from members import logic, utils
from members.constants import DEFAULT_PAGINATION
from events.helpers.views import search_filtered_queryset
from members.forms import SignupPersonForm, SignupOrganizationForm
from members.models import Person, Organization, Category, Member, Quota, Payment, PaymentStrategy

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


class AppLandingView(TemplateView):
    template_name = 'members/app_landing.html'


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
        currently = now()
        default_year, default_month = logic.decrement_year_month(currently.year, currently.month)
        try:
            year = int(request.GET.get('limit_year', default_year))
            month = int(request.GET.get('limit_month', default_month))
        except (KeyError, ValueError):
            year, month = default_year, default_month
        return year, month

    def get(self, request):
        """Produce the report with the given year/month limits."""
        limit_year, limit_month = self._get_yearmonth(request)
        category_filter = request.GET.get('category', None)
        debt_range_filter = request.GET.get('debt_range', None)

        # get those already confirmed members
        members_qs = Member.objects\
            .filter(legal_id__isnull=False, category__fee__gt=0, shutdown_date__isnull=True)\
            .select_related('category', 'person', 'organization')\
            .order_by('legal_id')

        if category_filter:
            members_qs = members_qs.filter(category__name=category_filter)

        debts = []
        summary_counts = {'small': 0, 'medium': 0, 'large': 0}

        category_icons = {
            'Activo': '⭐ Activo',
            'Adherente': '🤝 Adherente',
            'Afiliado': '🤝 Afiliado',
            'Honorario': '🎖️ Honorario'
        }

        for member in members_qs:
            if not member.registration_date:
                continue
            debt = logic.get_debt_state(member, limit_year, limit_month)
            if debt:
                d_len = len(debt)
                if 1 < d_len <= 3:
                    summary_counts['small'] += 1
                    r_type = 'small'
                elif 3 < d_len <= 12:
                    summary_counts['medium'] += 1
                    r_type = 'medium'
                elif d_len > 12:
                    summary_counts['large'] += 1
                    r_type = 'large'
                else:
                    r_type = 'other'

                if debt_range_filter and debt_range_filter != r_type:
                    continue

                cat_name = member.category.name if member.category else ''
                fee = member.category.fee if member.category else 0
                debt_amount = d_len * fee
                debts.append({
                    'member': member,
                    'category_display': category_icons.get(cat_name, cat_name),
                    'debt': utils.build_debt_string(debt),
                    'debt_len': d_len,
                    'debt_type': r_type,
                    'debt_amount': debt_amount,
                })

        sort_by = request.GET.get('sort', 'legal_id')
        direction = request.GET.get('dir', 'asc')
        reverse = (direction == 'desc')

        sort_keys = {
            'legal_id': lambda x: (x['member'].legal_id is None, x['member'].legal_id),
            'name': lambda x: str(x['member'].entity),
            'email': lambda x: str(x['member'].entity.email),
            'category': lambda x: str(x['member'].category),
            'debt_len': lambda x: x['debt_len'],
            'debt_amount': lambda x: x['debt_amount'],
            'document': lambda x: str(x['member'].entity.document_number),
        }
        
        key_func = sort_keys.get(sort_by, sort_keys['legal_id'])
        debts.sort(key=key_func, reverse=reverse)

        # Pagination support
        try:
            per_page = int(request.GET.get('per_page', DEFAULT_PAGINATION))
            if per_page not in [10, 20, 50, 100]:
                per_page = DEFAULT_PAGINATION
        except (ValueError, TypeError):
            per_page = DEFAULT_PAGINATION
        paginator = Paginator(debts, per_page)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context = {
            'debts': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'page_obj': page_obj,
            'paginator': paginator,
            'limit_year': limit_year,
            'limit_month': limit_month,
            'categories': Category.objects.all(),
            'summary_counts': summary_counts,
            'total_debtors': len(debts),
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


class DynamicPaginationMixin:
    def get_paginate_by(self, queryset):
        try:
            per_page = int(self.request.GET.get('per_page', DEFAULT_PAGINATION))
            if per_page in [10, 20, 50, 100]:
                return per_page
        except (ValueError, TypeError):
            pass
        return DEFAULT_PAGINATION


class MembersListView(LoginRequiredMixin, DynamicPaginationMixin, ListView):
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
        queryset = super().get_queryset().select_related('category', 'person', 'organization').prefetch_related('patron__paymentstrategy_set')
        category_filter = self.request.GET.get('category', None)
        category_name_filter = self.request.GET.get('category_name', None)
        if category_filter == 'Baja' or category_name_filter == 'Baja':
            pass
        else:
            queryset = queryset.filter(shutdown_date__isnull=True)
        search_value = self.request.GET.get('search', None)
        if search_value and search_value != '':
            queryset = search_filtered_queryset(queryset, self.search_fields, search_value)

        category_filter = self.request.GET.get('category', None)
        if category_filter:
            if category_filter == 'Baja':
                queryset = queryset.filter(shutdown_date__isnull=False)
            else:
                queryset = queryset.filter(category__name=category_filter)

        pending_filter = self.request.GET.get('pending', None)
        if pending_filter == 'true':
            queryset = queryset.filter(legal_id__isnull=True)

        category_name_filter = self.request.GET.get('category_name', None)
        if category_name_filter:
            if category_name_filter == 'Baja':
                queryset = queryset.filter(shutdown_date__isnull=False)
            elif category_name_filter == 'Sin categoría':
                queryset = queryset.filter(category__isnull=True)
            else:
                queryset = queryset.filter(category__name=category_name_filter)

        debt_status = self.request.GET.get('debt_status', None)
        debt_filter = self.request.GET.get('debt_filter', None)
        active_debt_filter = debt_status if debt_status in ['uptodate', 'small', 'medium', 'large', 'debtors'] else debt_filter
        if active_debt_filter:
            today = datetime.date.today()
            filtered_ids = []
            for m in queryset:
                if m.legal_id is None or not m.registration_date:
                    continue
                if m.category and m.category.fee == 0:
                    d_len = 0
                else:
                    debt = logic.get_debt_state(m, today.year, today.month)
                    d_len = len(debt) if debt else 0
                
                if active_debt_filter == 'uptodate' and d_len <= 1:
                    filtered_ids.append(m.pk)
                elif active_debt_filter == 'small' and 1 < d_len <= 3:
                    filtered_ids.append(m.pk)
                elif active_debt_filter == 'medium' and 3 < d_len <= 12:
                    filtered_ids.append(m.pk)
                elif active_debt_filter == 'large' and d_len > 12:
                    filtered_ids.append(m.pk)
                elif active_debt_filter == 'debtors' and d_len > 1:
                    filtered_ids.append(m.pk)
            queryset = queryset.filter(pk__in=filtered_ids)

        sort_by = self.request.GET.get('sort', 'legal_id')
        direction = self.request.GET.get('dir', 'asc')
        
        valid_sort_fields = {
            'legal_id': 'legal_id',
            'name': 'person__last_name',
            'email': 'person__email',
            'category': 'category__name',
            'document': 'person__document_number',
        }
        
        db_field = valid_sort_fields.get(sort_by, 'legal_id')
        if direction == 'desc':
            db_field = f'-{db_field}'
            
        return queryset.order_by(db_field)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.all()
        context['platforms'] = PaymentStrategy.PLATFORM_CHOICES

        strategy_icons = {
            'mercado pago': '💳 Mercado Pago',
            'todo pago': '💳 Todo Pago',
            'transfer': '🏦 Transferencia',
            'credit': '🎁 Crédito Bonificado'
        }

        category_icons = {
            'Activo': '⭐ Activo',
            'Adherente': '🤝 Adherente',
            'Afiliado': '🤝 Afiliado',
            'Honorario': '🎖️ Honorario'
        }

        today = datetime.date.today()
        for m in context.get('members_list', []):
            if (m.category and m.category.fee == 0) or not m.registration_date:
                m.debt_count = 0
            else:
                debt = logic.get_debt_state(m, today.year, today.month)
                m.debt_count = len(debt) if debt else 0
            
            last_strategy = '-'
            last_payment_date = '-'
            last_quota_str = '-'

            if m.patron:
                last_payment = Payment.objects.filter(strategy__patron=m.patron).order_by('-timestamp').first()
                if last_payment:
                    if last_payment.strategy:
                        raw_strat = last_payment.strategy.platform
                        last_strategy = strategy_icons.get(raw_strat, last_payment.strategy.platform_name)
                    last_payment_date = last_payment.timestamp.strftime('%Y-%m-%d')
                    
                    quotas = Quota.objects.filter(payment=last_payment).order_by('-year', '-month')
                    if quotas.exists():
                        latest_q = quotas.first()
                        last_quota_str = latest_q.code
                else:
                    strat = m.patron.paymentstrategy_set.first()
                    if strat:
                        raw_strat = strat.platform
                        last_strategy = strategy_icons.get(raw_strat, strat.platform_name)

            m.strategies_str = last_strategy
            m.last_payment_date = last_payment_date
            m.last_quota_str = last_quota_str
            
            cat_name = m.category.name if m.category else ''
            m.category_display = category_icons.get(cat_name, cat_name)

        all_members = Member.objects.filter(shutdown_date__isnull=True).select_related('category').prefetch_related('patron__paymentstrategy_set')
        
        categories_matrix = {}
        for cat in Category.objects.all():
            categories_matrix[cat.name] = {'uptodate': 0, 'small': 0, 'medium': 0, 'large': 0}
        categories_matrix['Sin categoría'] = {'uptodate': 0, 'small': 0, 'medium': 0, 'large': 0}

        total_active = 0
        total_up_to_date = 0
        total_debt = 0
        total_pending = 0

        for m in all_members:
            if m.legal_id is None or not m.registration_date:
                total_pending += 1
                continue

            total_active += 1
            if (m.category and m.category.fee == 0) or not m.registration_date:
                debt_len = 0
            else:
                debt = logic.get_debt_state(m, today.year, today.month)
                debt_len = len(debt) if debt else 0
            
            m.debt_count = debt_len
            strategies = []
            if m.patron:
                strategies = [s.platform_name for s in m.patron.paymentstrategy_set.all()]
            m.strategies_str = ', '.join(strategies) if strategies else '-'

            cat_name = m.category.name if m.category else 'Sin categoría'
            if cat_name not in categories_matrix:
                categories_matrix[cat_name] = {'uptodate': 0, 'small': 0, 'medium': 0, 'large': 0}

            if debt_len <= 1:
                total_up_to_date += 1
                categories_matrix[cat_name]['uptodate'] += 1
            else:
                total_debt += 1

            if 1 < debt_len <= 3:
                categories_matrix[cat_name]['small'] += 1
            elif 3 < debt_len <= 12:
                categories_matrix[cat_name]['medium'] += 1
            elif debt_len > 12:
                categories_matrix[cat_name]['large'] += 1

        filtered_categories_matrix = {}
        zero_categories = []
        for cat_name, counts in categories_matrix.items():
            total_count = counts['uptodate'] + counts['small'] + counts['medium'] + counts['large']
            if total_count > 0:
                filtered_categories_matrix[cat_name] = counts
            else:
                zero_categories.append(cat_name)

        total_shutdown = Member.objects.filter(shutdown_date__isnull=False).count()
        total_members = total_up_to_date + total_debt + total_pending + total_shutdown

        context['summary'] = {
            'total_members': total_members,
            'total_up_to_date': total_up_to_date,
            'total_debt': total_debt,
            'total_pending': total_pending,
            'total_shutdown': total_shutdown,
            'categories_matrix': filtered_categories_matrix,
            'zero_categories': zero_categories,
        }
        return context

    def get(self, request, *args, **kwargs):
        """
            If get one result when call self.get_queryset() then
            redirect to member_detail view, else display the filtered
            list of members
        """
        # Only redirect if search is direct and unique, not when filtering by dropdowns
        search_value = request.GET.get('search', None)
        if search_value and search_value != '' and not request.GET.get('category') and not request.GET.get('strategy'):
            if self.get_queryset().count() == 1:
                return redirect('member_detail', self.get_queryset().first().pk)
        return super().get(request, *args, **kwargs)


class MemberDetailView(LoginRequiredMixin, DetailView):
    model = Member
    template_name = 'members/member_detail.html'

    def _get_last_payments(self, member):
        """Get the info for last payments and activity history."""
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
                'type': 'payment'
            })

        if member.shutdown_date:
            info.append({
                'title': "Baja de Socio",
                'timestamp': member.shutdown_date.strftime('%Y-%m-%d 00:00:00'),
                'invoice': 'N/A',
                'quotas': '-',
                'type': 'shutdown'
            })

        info = sorted(info, key=lambda x: x['timestamp'], reverse=True)
        return info

    def get_context_data(self, **kwargs):
        # Get the context from base
        context = super().get_context_data(**kwargs)
        member = self.get_object()
        today = datetime.date.today()
        debt = logic.get_debt_state(member, today.year, today.month)
        if (member.category and member.category.fee == 0) or not member.registration_date:
            debt_count = 0
            debt_amount = 0
        else:
            debt_count = len(debt) if debt else 0
            fee = member.category.fee if member.category else 0
            debt_amount = debt_count * fee

        context['debt_count'] = debt_count
        context['debt_amount'] = debt_amount

        last_payment = Payment.objects.filter(strategy__patron=member.patron).order_by('-timestamp').first() if member.patron else None
        last_payment_date = last_payment.timestamp.strftime('%Y-%m-%d') if last_payment else '-'
        latest_quota = Quota.objects.filter(member=member).order_by('-year', '-month').first()
        last_quota_str = latest_quota.code if latest_quota else '-'

        context['last_payment_date'] = last_payment_date
        context['last_quota_str'] = last_quota_str

        if len(debt) > 1 and member.category and member.category.fee > 0:
            context['debtor'] = True
        context['member'] = member
        context['last_payments_info'] = self._get_last_payments(member)
        context['missing_letter'] = not member.has_subscription_letter
        context['all_categories'] = Category.objects.all()
        return context


class MemberEditPersonView(OnlyAdminsViewMixin, View):
    def get(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        if not member.person:
            messages.error(request, "Este miembro no es una persona física.")
            return redirect('member_detail', pk=pk)
        form = SignupPersonForm(instance=member.person)
        return render(request, 'members/member_edit_form.html', {'form': form, 'member': member, 'title': 'Editar Persona'})

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        if not member.person:
            messages.error(request, "Este miembro no es una persona física.")
            return redirect('member_detail', pk=pk)
        form = SignupPersonForm(request.POST, request.FILES, instance=member.person)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos personales actualizados correctamente.")
            return redirect('member_detail', pk=pk)
        return render(request, 'members/member_edit_form.html', {'form': form, 'member': member, 'title': 'Editar Persona'})


class MemberEditOrganizationView(OnlyAdminsViewMixin, View):
    def get(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        if not member.organization:
            messages.error(request, "Este miembro no es una organización.")
            return redirect('member_detail', pk=pk)
        form = SignupOrganizationForm(instance=member.organization)
        return render(request, 'members/member_edit_form.html', {'form': form, 'member': member, 'title': 'Editar Organización'})

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        if not member.organization:
            messages.error(request, "Este miembro no es una organización.")
            return redirect('member_detail', pk=pk)
        form = SignupOrganizationForm(request.POST, request.FILES, instance=member.organization)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos de la organización actualizados correctamente.")
            return redirect('member_detail', pk=pk)
        return render(request, 'members/member_edit_form.html', {'form': form, 'member': member, 'title': 'Editar Organización'})


class MemberEditPatronView(OnlyAdminsViewMixin, View):
    def get(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        if not member.patron:
            messages.error(request, "Este miembro no tiene un patrón asignado.")
            return redirect('member_detail', pk=pk)
        form = PatronForm(instance=member.patron)
        return render(request, 'members/member_edit_form.html', {'form': form, 'member': member, 'title': 'Editar Patron'})

    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        if not member.patron:
            messages.error(request, "Este miembro no tiene un patrón asignado.")
            return redirect('member_detail', pk=pk)
        form = PatronForm(request.POST, instance=member.patron)
        if form.is_valid():
            form.save()
            messages.success(request, "Datos del patron actualizados correctamente.")
            return redirect('member_detail', pk=pk)
        return render(request, 'members/member_edit_form.html', {'form': form, 'member': member, 'title': 'Editar Patron'})


class MemberShutdownView(OnlyAdminsViewMixin, View):
    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        action = request.POST.get('action')
        if action == 'shutdown':
            shutdown_date_str = request.POST.get('shutdown_date')
            if shutdown_date_str:
                try:
                    shutdown_date = datetime.datetime.strptime(shutdown_date_str, '%Y-%m-%d').date()
                except ValueError:
                    shutdown_date = datetime.date.today()
            else:
                shutdown_date = datetime.date.today()
            member.shutdown_date = shutdown_date
            
            baja_cat, _ = Category.objects.get_or_create(
                name='Baja',
                defaults={'description': 'Categoría para socios dados de baja', 'fee': 0}
            )
            member.category = baja_cat
            member.save()
            messages.success(request, f"Socio {member.entity} dado de baja correctamente.")
        elif action == 'reactivate':
            member.shutdown_date = None
            messages.success(request, f"Socio {member.entity} reactivado correctamente. Por favor, reasigne su categoría correspondiente.")
            member.save()
        return redirect('member_detail', pk=pk)


class MemberChangeCategoryView(OnlyAdminsViewMixin, View):
    def post(self, request, pk):
        member = get_object_or_404(Member, pk=pk)
        if member.shutdown_date or (member.category and member.category.name == 'Baja'):
            messages.error(request, "No se puede cambiar la categoría de un socio que se encuentra dado de baja.")
            return redirect('member_detail', pk=pk)
        cat_id = request.POST.get('category')
        category = get_object_or_404(Category, pk=cat_id)
        if category.name == 'Baja':
            messages.error(request, "No se puede seleccionar la categoría Baja de forma manual.")
            return redirect('member_detail', pk=pk)
        old_cat = member.category
        member.category = category
        member.save()
        messages.success(request, f"Categoría cambiada de '{old_cat}' a '{category.name}' correctamente.")
        return redirect('member_detail', pk=pk)


class MemberMarkSignedView(OnlyAdminsViewMixin, View):
    def post(self, request, pk=None):
        if pk:
            member = get_object_or_404(Member, pk=pk)
            member.has_subscription_letter = True
            member.save()
            messages.success(request, f"Se ha marcado la carta de asociación como firmada para {member.entity}.")
            return redirect('member_detail', pk=pk)
        
        to_member_ids = request.POST.getlist('sendmail')
        if to_member_ids:
            Member.objects.filter(pk__in=to_member_ids).update(has_subscription_letter=True)
            messages.success(request, "Se ha marcado la carta de asociación como firmada para los miembros seleccionados.")
        return redirect('report_missing')


# public
signup_initial = SignupInitialView.as_view()
signup_form_person = SignupPersonFormView.as_view()
signup_form_organization = SignupOrganizationsFormView.as_view()
signup_person_thankyou = SignupPersonThankyouView.as_view()
signup_organization_thankyou = SignupOrganizationThankyouView.as_view()
# only admins
reports_main = ReportsInitialView.as_view()
app_landing = AppLandingView.as_view()
report_debts = ReportDebts.as_view()
report_missing = ReportMissing.as_view()
report_complete = ReportComplete.as_view()
report_income_quotas = ReportIncomeQuotas.as_view()
report_income_money = ReportIncomeMoney.as_view()
members_list = MembersListView.as_view()
member_detail = MemberDetailView.as_view()
member_edit_person = MemberEditPersonView.as_view()
member_edit_org = MemberEditOrganizationView.as_view()
member_edit_patron = MemberEditPatronView.as_view()
member_shutdown = MemberShutdownView.as_view()
member_change_category = MemberChangeCategoryView.as_view()
member_mark_signed = MemberMarkSignedView.as_view()
