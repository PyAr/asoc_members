from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from .models import Member, Person, Organization, Patron, Payment, PaymentStrategy, Quota


class PersonNoMembers(SimpleListFilter):
    title = 'person no member' # or use _('country') for translated title
    parameter_name = 'membership'

    def lookups(self, request, model_admin):
       return (
           ('filtered', 'Member in progress'),
        )

    def queryset(self, request, queryset):
        if self.value() == 'filtered':
            return queryset.filter(membership__isnull=True)
        return queryset


class PersonAdmin(admin.ModelAdmin):
    list_filter = (PersonNoMembers, )


admin.site.register(Member)
admin.site.register(Person, PersonAdmin)
admin.site.register(Organization)
admin.site.register(Patron)
admin.site.register(Payment)
admin.site.register(PaymentStrategy)
admin.site.register(Quota)
