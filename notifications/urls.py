from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # User notifications
    path('', views.NotificationListView.as_view(), name='notification-list'),
    path('<int:notification_id>/read/', views.mark_notification_read_view, name='mark-notification-read'),
    path('mark-all-read/', views.mark_all_notifications_read_view, name='mark-all-read'),
    path('count/', views.notification_count_view, name='notification-count'),

    # Email templates (admin only)
    path('templates/', views.EmailTemplateListView.as_view(), name='email-template-list'),
    path('templates/<int:pk>/', views.EmailTemplateDetailView.as_view(), name='email-template-detail'),
]