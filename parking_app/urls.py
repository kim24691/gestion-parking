from django.urls import path
from . import views

urlpatterns = [
    # Tableau de bord principal
    path('', views.dashboard, name='dashboard'),

    # Authentification & Profil
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.profile_view, name='profile'),

    # Module Stationnements & Tickets
    path('tickets/', views.ticket_list, name='ticket_list'),
    path('tickets/entry/', views.ticket_entry, name='ticket_entry'),
    path('tickets/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:pk>/checkout/', views.ticket_checkout, name='ticket_checkout'),
    path('tickets/<int:pk>/print/', views.ticket_print, name='ticket_print'),
    path('tickets/<int:pk>/pdf/', views.ticket_pdf, name='ticket_pdf'),
    path('tickets/<int:pk>/deactivate/', views.ticket_deactivate, name='ticket_deactivate'),
    path('tickets/<int:pk>/delete/', views.ticket_delete, name='ticket_delete'),

    # Module Zones de Parking
    path('zones/', views.zone_list, name='zone_list'),
    path('zones/create/', views.zone_create, name='zone_create'),
    path('zones/<int:pk>/edit/', views.zone_edit, name='zone_edit'),
    path('zones/<int:pk>/toggle/', views.zone_toggle_status, name='zone_toggle_status'),

    # Module Tarification & Types de Véhicules
    path('tariffs/', views.tariff_list, name='tariff_list'),
    path('tariffs/create/', views.tariff_create, name='tariff_create'),
    path('tariffs/<int:pk>/edit/', views.tariff_edit, name='tariff_edit'),
    path('tariffs/<int:pk>/delete/', views.tariff_delete, name='tariff_delete'),
    path('vehicle-types/create/', views.vehicle_type_create, name='vehicle_type_create'),
    path('vehicle-types/<int:pk>/edit/', views.vehicle_type_edit, name='vehicle_type_edit'),

    # Module Gestion des Utilisateurs (Administrateur)
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/toggle/', views.user_toggle_status, name='user_toggle_status'),

    # Module Traçabilité & Audit Trail
    path('audit/', views.audit_log_list, name='audit_log_list'),

    # Module Rapports & Impression
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/traffic/', views.report_daily_traffic, name='report_daily_traffic'),
    path('reports/financial/', views.report_financial, name='report_financial'),
    path('reports/violations/', views.report_violations, name='report_violations'),

    # API JSON pour Chart.js (Dashboard Admin)
    path('api/dashboard-chart-data/', views.api_dashboard_chart_data, name='api_dashboard_chart_data'),
]
