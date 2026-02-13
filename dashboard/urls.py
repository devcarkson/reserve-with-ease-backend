from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # User Dashboard
    path('user/', views.user_dashboard_view, name='user-dashboard'),

    # Owner Dashboard
    path('owner/', views.owner_dashboard_view, name='owner-dashboard'),

    # Admin Dashboard
    path('admin/', views.admin_dashboard_view, name='admin-dashboard'),

    # Performance Overview
    path('performance/overview/', views.performance_overview_view, name='performance-overview'),

    # Reservation Performance
    path('performance/reservations/', views.reservation_performance_view, name='reservation-performance'),

    # User Activity
    path('activity/', views.user_activity_view, name='user-activity'),

    # System Alerts
    path('alerts/', views.system_alerts_view, name='system-alerts'),
    path('alerts/<int:alert_id>/read/', views.mark_alert_read_view, name='mark-alert-read'),

    # Platform Stats (public - for login page)
    path('platform/stats/', views.platform_stats_view, name='platform-stats'),
    
    # Track Visit (public)
    path('platform/track-visit/', views.track_visit_view, name='track-visit'),
]
