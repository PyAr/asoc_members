from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path, include
from . import views

urlpatterns = [
     path('', views.events_home, name='events_home'),
     # Events urls.
     path('eventos/', views.events_list, name='event_list'),
     path('eventos/<pk>/', views.event_detail, name='event_detail'),
     path('eventos/<pk>/editar/', views.event_change, name='event_change'),
     path(
          'eventos/<pk>/agregar-categoria-sponsor/',
          views.event_create_sponsor_category,
          name='event_create_sponsor_category'
     ),

     # Sponsoring urls.
     path('eventos/<event_pk>/patrocinios/', views.sponsoring_list, name='sponsoring_list'),
     path('eventos/<event_pk>/patrocinios/crear/', views.sponsoring_create, name='sponsoring_create'),

     # Organizers urls.
     path('registrar-organizador/', views.organizer_signup, name='organizer_signup'),
     path('organizadores/', views.organizers_list, name='organizer_list'),
     path('organizadores/<pk>/', views.organizer_detail, name='organizer_detail'),
     path('organizadores/<pk>/editar/', views.organizer_change, name='organizer_change'),
     path(
          'organizadores/<pk>/agregar-cuenta-bancaria/',
          views.organizer_create_bank_account_data,
          name='organizer_create_bank_account_data'
     ),
     path(
          'cuenta-bancaria/<pk>/editar/',
          views.organizer_update_bank_account_data,
          name='organizer_update_bank_account_data'
     ),

     # Sponsors urls.
     path('patrocinadores/', views.sponsors_list, name='sponsor_list'),
     path('patrocinadores/crear/', views.sponsor_create, name='sponsor_create'),
     path('patrocinadores/<pk>/', views.sponsor_detail, name='sponsor_detail'),
     path('patrocinadores/<pk>/editar/', views.sponsor_change, name='sponsor_change'),
     path('patrocinadores/<pk>/habilitar/', views.sponsor_set_enabled, name='sponsor_set_enabled'),

     # Others

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
