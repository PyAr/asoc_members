from django.urls import path

from members import views


urlpatterns = [
    path('solicitud-alta/', views.signup_initial, name='signup'),
    path('solicitud-alta/persona/', views.signup_form_person, name='signup_person'),
    path('solicitud-alta/organizacion', views.signup_form_organization, name='signup_organization'),
    path('solicitud-alta/gracias', views.signup_thankyou, name='signup_thankyou'),


]
