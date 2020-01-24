from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from . import views

urlpatterns = [
    path('', views.events_home, name='events_home'),
    # Events urls.
    path('eventos/', views.events_list, name='event_list'),
    path('eventos/<pk>/configuracion/', views.event_detail, name='event_detail'),
    path('eventos/<pk>/editar/', views.event_change, name='event_change'),
    path(
        'eventos/<pk>/agregar-categoria-sponsor/',
        views.event_create_sponsor_category,
        name='event_create_sponsor_category'
    ),

    # Sponsoring urls.
    path('eventos/<event_pk>/patrocinios/', views.sponsoring_list, name='sponsoring_list'),
    path(
        'eventos/<event_pk>/patrocinios/crear/',
        views.sponsoring_create,
        name='sponsoring_create'
    ),
    path(
        'eventos/patrocinios/<pk>/',
        views.sponsoring_detail,
        name='sponsoring_detail'
    ),

    path(
        'eventos/patrocinios/<pk>/cerrar',
        views.sponsoring_set_close,
        name='sponsoring_set_close'
    ),
    path(
        'eventos/patrocinios/<pk>/factura/crear/',
        views.sponsoring_invoice_create,
        name='sponsoring_invoice_create'
    ),

    path(
        'eventos/factura/<pk>/afectacion/crear/',
        views.sponsoring_invoice_affect_create,
        name='sponsoring_invoice_affect_create'
    ),

    # Expenses urls.
    path('eventos/<event_pk>/gastos/', views.expenses_list, name='expenses_list'),
    path(
        'eventos/<event_pk>/gastos/proveedor/crear/',
        views.provider_expense_create,
        name='provider_expense_create'
    ),
    path(
        'eventos/<event_pk>/gastos/organizador/crear/',
        views.organizer_refund_create,
        name='organizer_refund_create'
    ),
    path(
        'eventos/gasto_proveedor/<pk>/',
        views.provider_expense_detail,
        name='provider_expense_detail'
    ),
    path(
        'eventos/gasto_proveedor/<pk>/editar/',
        views.provider_expense_update,
        name='provider_expense_update'
    ),
    path(
        'eventos/gasto_proveedor/<pk>/switch/',
        views.provider_expense_switch_state,
        name='provider_expense_switch_state'
    ),
    path(
        'eventos/reintegro/<pk>/',
        views.organizer_refund_detail,
        name='organizer_refund_detail'
    ),
    path(
        'eventos/gasto_proveedor/<pk>/pago/crear/',
        views.provider_expense_payment_create,
        name='provider_expense_payment_create'
    ),
    path(
        'organizadores/<pk>/reintegros/pagar/',
        views.organizer_refund_payment_create,
        name='organizer_refund_payment_create'
    ),
    path(
        'organizadores/<pk>/reintegros/switch/',
        views.organizer_refund_switch_state,
        name='organizer_refund_switch_state'
    ),
    # Invoice actions urls.
    path(
        'eventos/factura/<pk>/aprobar/',
        views.invoice_set_approved,
        name='invoice_set_approved'
    ),
    path(
        'eventos/factura/<pk>/setear-pago-completo/',
        views.invoice_set_complete_payment,
        name='invoice_set_complete_payment'
    ),
    path(
        'eventos/factura/<pk>/setear-pago-parcial/',
        views.invoice_set_partial_payment,
        name='invoice_set_partial_payment'
    ),

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

    # Providers urls.
    path('proveedores/', views.providers_list, name='provider_list'),
    path('proveedores/crear/', views.provider_create, name='provider_create'),
    path('proveedores/<pk>/', views.provider_detail, name='provider_detail'),
    path('proveedores/<pk>/editar/', views.provider_change, name='provider_change'),

    # Others

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
