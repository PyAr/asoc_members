from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from .models import Member, Person, Organization, Patron, Payment, PaymentStrategy, Quota


class PersonNoMembers(SimpleListFilter):
    title = 'signup process'
    parameter_name = 'membership'

    def lookups(self, request, model_admin):
       return (
           ('filtered', 'Signup in progress'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'filtered':
            return queryset.filter(membership__isnull=True)
        return queryset


class OrganizationNoMembers(SimpleListFilter):
    title = 'signup process'
    parameter_name = 'membership'

    def lookups(self, request, model_admin):
       return (
           ('filtered', 'Signup in progress'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'filtered':
            return queryset.filter(membership__isnull=True)
        return queryset


class PersonAdmin(admin.ModelAdmin):
    list_filter = (PersonNoMembers, )
    list_display = ('first_name', 'last_name', 'document_number', 'nickname' )
    search_fields = ('^first_name', '^last_name', '^document_number', )
    list_display_links = ('first_name', 'last_name', )


class MemberAdmin(admin.ModelAdmin):
    list_display = ('legal_id', 'person', 'organization', 'registration_date')
    list_filter = ('category', )
    search_fields = ('^legal_id', 'person__first_name', 'person__last_name', )
    list_display_links = ('legal_id', )


class OrganizationAdmin(admin.ModelAdmin):
    list_filter = (OrganizationNoMembers, )
    list_display = ('name', 'document_number', 'address', )
    search_fields = ('^name', '^document_number', )
    list_display_links = ('name', )


class PatronAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'comments', )
    search_fields = ('^name', '^email', )
    list_display_links = ('name', )


class PaymentStrategyAdmin(admin.ModelAdmin):
    list_filter = ('platform', )
    list_display = ('platform', 'id_in_platform', 'patron', 'comments')
    search_fields = ('^patron__name', )
    list_display_links = ('id_in_platform', )


class PaymentAdmin(admin.ModelAdmin):
    list_filter = ('strategy', )
    list_display = (
        'timestamp', 'amount', 'comments')
    search_fields = ('^patron__name', )
    list_display_links = ('timestamp', )



class QuotaAdmin(admin.ModelAdmin):
    list_filter = ('year', 'month', )
    list_display = ('payment', 'year', 'month', 'amount', 'member')
    search_fields = ('^member__person__first_name', '^member__person__last_name', )
    list_display_links = ('payment', )


admin.site.register(Member, MemberAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Organization, OrganizationAdmin)
admin.site.register(Patron, PatronAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(PaymentStrategy, PaymentStrategyAdmin)
admin.site.register(Quota, QuotaAdmin)
