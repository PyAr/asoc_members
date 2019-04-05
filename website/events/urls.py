from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.urls import path, include

urlpatterns = [
     #path('cuentas/login/', auth_views.login, name='login'),
     path('cuentas/login/', auth_views.LoginView.as_view(), name='login'),
     path('cuentas/', include('django.contrib.auth.urls')),
     
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
