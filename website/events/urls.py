from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path, include
from . import views

urlpatterns = [
     #path('cuentas/login/', auth_views.login, name='login'),
     path('', views.events_home, name='events_home'),
     path('eventos/', views.events_list, name='event_list'),
     path('eventos/<pk>/', views.event_detail, name='event_detail'),
     path('eventos/<pk>/editar/', views.event_change, name='event_change'),
     path('eventos/<pk>/agregar-categoria-sponsor/', views.event_create_sponsor_category, name='event_create_sponsor_category'),

     path('registrar-organizador/', views.organizer_signup, name='organizer_signup'),
     path('organizadores/', views.organizers_list, name='organizer_list'),
     path('organizadores/<pk>/', views.organizer_detail, name='organizer_detail'),
     path('organizadores/<pk>/editar/', views.organizer_change, name='organizer_change'),
     
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
