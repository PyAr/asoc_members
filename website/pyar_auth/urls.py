from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetDoneView,
    LogoutView
    )
from pyar_auth import views

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('cambio-clave/', views.PasswordResetView.as_view(), name='password_reset'),
    path('cambio-clave/finalizado', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('<uidb64>/<token>/', 
         views.PasswordResetConfirmView.as_view(),
         name='password_reset_confirm'),
    path('cambio-clave-completo/',
         PasswordResetCompleteView.as_view(),
         name='password_reset_complete'),
    path('clave/', views.change_password, name='change_password'),
    path('perfil/', views.ProfileView.as_view(), name='profile'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
