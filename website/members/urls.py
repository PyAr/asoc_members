from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from members import views

urlpatterns = [
    path('solicitud-alta/', views.signup_initial, name='signup'),
    path('solicitud-alta/persona/', views.signup_form_person, name='signup_person'),
    path('solicitud-alta/organizacion',
         views.signup_form_organization, name='signup_organization'),
    path('solicitud-alta/gracias', views.signup_thankyou, name='signup_thankyou'),

    path('reportes/', views.reports_main, name='reports_main'),
    path('reportes/deudas', views.report_debts, name='report_debts'),
    path('reportes/completos', views.report_complete, name='report_complete'),
    path('reportes/incompletos', views.report_missing, name='report_missing'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
