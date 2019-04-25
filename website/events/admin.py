from django.contrib import admin
from django.contrib.sites.shortcuts import get_current_site
import events
from events.helpers.notifications import email_notifier
from events.models import Event, Organizer, EventOrganizer


class EventOrganizerInline(admin.TabularInline):
    model = EventOrganizer
    extra = 1

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    fields = ('name', 'commission', 'category','start_date', 'place')
    inlines = (EventOrganizerInline,)
    list_display = ('name', 'start_date', 'place', 'category' )
    search_fields = ('start_date', 'place', )
    list_filter = ('category', )
    
    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        event_instance = form.save(commit=False)
        notify_organizers = []
        for instance in instances:
            if type(instance)==EventOrganizer:
                exists_organizer = EventOrganizer.objects.filter(event=instance.event, organizer=instance.organizer).exists()            
                if not exists_organizer:
                    notify_organizers.append(instance.organizer)
            
        super(EventAdmin, self).save_formset(request, form, formset, change)
        if len(notify_organizers):
            current_site = get_current_site(request)
            context={
                'domain': current_site.domain,
                'protocol': 'https' if request.is_secure() else 'http'
            }
            email_notifier.send_organizer_associated_to_event(event_instance, notify_organizers, context)    


#TODO: unregister just to develop
@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    fields = ('first_name', 'last_name', 'user')
    list_display = ('username', 'email', 'first_name', 'last_name' )
    search_fields = ('user__email', 'first_name', 'last_name' )
    readonly_fields = ('first_name', 'last_name', 'user')

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def username(self, obj):
        return obj.user.username