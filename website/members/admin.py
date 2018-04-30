from django.contrib import admin

from .models import Member, Person, Organization, Patron, Payment, PaymentStrategy, Quota


admin.site.register(Member)
admin.site.register(Person)
admin.site.register(Organization)
admin.site.register(Patron)
admin.site.register(Payment)
admin.site.register(PaymentStrategy)
admin.site.register(Quota)
