from django.contrib import admin
from .models import EmailTemplate, EmailNotification, Notification


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'template_type', 'is_active', 'updated_at']
    list_filter = ['template_type', 'is_active']
    search_fields = ['name', 'subject']


@admin.register(EmailNotification)
class EmailNotificationAdmin(admin.ModelAdmin):
    list_display = ['recipient', 'subject', 'status', 'sent_at', 'retry_count']
    list_filter = ['status', 'created_at', 'sent_at']
    search_fields = ['recipient', 'subject']
    readonly_fields = ['sent_at', 'error_message', 'retry_count']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__username', 'title', 'message']
    readonly_fields = ['read_at']