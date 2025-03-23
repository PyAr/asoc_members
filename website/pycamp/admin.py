from django.contrib import admin
from .models import Pycamp, Camper, CamperPerson, Project, Vote, Slot, WizardTimeframe

class CamperInline(admin.TabularInline):
    model = Camper
    extra = 1
    fields = ('person', 'wizard')

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        formset.form.base_fields['person'].widget.can_add_related = True
        formset.form.base_fields['person'].widget.can_change_related = True
        return formset

@admin.register(Pycamp)
class PycampAdmin(admin.ModelAdmin):
    list_display = ('headquarters', 'init', 'end', 'vote_authorized', 'project_load_authorized', 'get_attendants_count')
    list_filter = ('headquarters', 'init', 'vote_authorized', 'project_load_authorized')
    search_fields = ('headquarters',)
    inlines = [CamperInline]

    def get_attendants_count(self, obj):
        return obj.campers.count()
    get_attendants_count.short_description = 'Attendants'

@admin.register(CamperPerson)
class CamperPersonAdmin(admin.ModelAdmin):
    list_display = ('username', 'chat_id')
    search_fields = ('username', 'chat_id')

# Register other models with basic admin interface
admin.site.register(Project)
admin.site.register(Vote)
admin.site.register(Slot)
admin.site.register(WizardTimeframe)
