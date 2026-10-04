from django.conf import settings
from django.conf.urls.static import static
from django.urls import path

from members import views

urlpatterns = [
    path('', views.app_landing, name='app_landing'),
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
    path('reportes/miembros/<pk>/editar/persona/', views.member_edit_person, name='member_edit_person'),
    path('reportes/miembros/<pk>/editar/organizacion/', views.member_edit_org, name='member_edit_org'),
    path('reportes/miembros/<pk>/editar/patron/', views.member_edit_patron, name='member_edit_patron'),
    path('reportes/miembros/<pk>/baja/', views.member_shutdown, name='member_shutdown'),
    path('reportes/miembros/<pk>/cambiar-categoria/', views.member_change_category, name='member_change_category'),
    path('reportes/miembros/<pk>/firmar-carta/', views.member_mark_signed, name='member_mark_signed'),
    path('reportes/incompletos/firmar-carta/', views.member_mark_signed, name='members_mark_signed_bulk'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
