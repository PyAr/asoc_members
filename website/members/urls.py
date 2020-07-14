from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from members import views

urlpatterns = [
    path('solicitud-alta/', views.signup_initial, name='signup'),
    path('solicitud-alta/persona/', views.signup_form_person, name='signup_person'),
    path('solicitud-alta/persona/gracias',
         views.signup_person_thankyou, name='signup_person_thankyou'),
    path('solicitud-alta/organizacion',
         views.signup_form_organization, name='signup_organization'),
    path('solicitud-alta/organizacion/gracias',
         views.signup_organization_thankyou, name='signup_organization_thankyou'),

    path('reportes/', views.reports_main, name='reports_main'),
    path('reportes/deudas', views.report_debts, name='report_debts'),
    path('reportes/completos', views.report_complete, name='report_complete'),
    path('reportes/incompletos', views.report_missing, name='report_missing'),
    path('reportes/ingcuotas', views.report_income_quotas, name='report_income_quotas'),
    path('reportes/ingdinero', views.report_income_money, name='report_income_money'),


    path('reportes/miembros', views.members_list, name="members_list"),
    path('reportes/miembros/<pk>/', views.member_detail, name='member_detail'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
