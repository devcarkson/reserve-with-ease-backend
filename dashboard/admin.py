from django.contrib import admin
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from django.contrib.auth import get_user_model
from properties.models import Property
from reservations.models import Reservation
from reviews.models import Review
from .models import (
    UserDashboardStats, OwnerDashboardStats, AdminDashboardStats,
    RevenueAnalytics, BookingAnalytics, PropertyPerformance,
    UserActivity, SystemAlert, DashboardWidget, Report,
    NotificationPreference
)

User = get_user_model()


class UserDashboardStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'total_reservations', 'total_spent', 'last_login', 'updated_at']
    list_filter = ['last_login', 'updated_at']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']


class OwnerDashboardStatsAdmin(admin.ModelAdmin):
    list_display = ['owner', 'total_properties', 'total_reservations', 'total_revenue', 'average_rating', 'updated_at']
    list_filter = ['updated_at']
    search_fields = ['owner__username', 'owner__email']
    readonly_fields = ['created_at', 'updated_at']


class AdminDashboardStatsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_users', 'total_properties', 'total_reservations', 'total_revenue', 'average_rating']
    list_filter = ['date']
    readonly_fields = ['created_at']


class RevenueAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['user', 'property', 'period', 'date', 'revenue', 'bookings']
    list_filter = ['period', 'date']
    search_fields = ['user__username', 'property__name']


class BookingAnalyticsAdmin(admin.ModelAdmin):
    list_display = ['user', 'property', 'date', 'bookings', 'cancellations', 'conversion_rate']
    list_filter = ['date']
    search_fields = ['user__username', 'property__name']


class PropertyPerformanceAdmin(admin.ModelAdmin):
    list_display = ['property', 'date', 'views', 'bookings', 'conversion_rate', 'revenue']
    list_filter = ['date']
    search_fields = ['property__name']


class UserActivityAdmin(admin.ModelAdmin):
    list_display = ['user', 'activity_type', 'description', 'created_at']
    list_filter = ['activity_type', 'created_at']
    search_fields = ['user__username', 'description']
    readonly_fields = ['created_at']


class SystemAlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'alert_type', 'priority', 'user', 'is_read', 'created_at']
    list_filter = ['alert_type', 'priority', 'is_read', 'created_at']
    search_fields = ['title', 'message', 'user__username']
    readonly_fields = ['created_at']


class DashboardWidgetAdmin(admin.ModelAdmin):
    list_display = ['name', 'widget_type', 'user', 'is_visible', 'position_x', 'position_y']
    list_filter = ['widget_type', 'is_visible']
    search_fields = ['name', 'user__username']


class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'user', 'status', 'generated_at', 'created_at']
    list_filter = ['report_type', 'status', 'created_at']
    search_fields = ['name', 'user__username']
    readonly_fields = ['created_at', 'generated_at']


class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = ['user', 'notification_type', 'email_enabled', 'sms_enabled', 'push_enabled']
    list_filter = ['notification_type', 'email_enabled', 'sms_enabled', 'push_enabled']
    search_fields = ['user__username', 'notification_type']


# Register all models
admin.site.register(UserDashboardStats, UserDashboardStatsAdmin)
admin.site.register(OwnerDashboardStats, OwnerDashboardStatsAdmin)
admin.site.register(AdminDashboardStats, AdminDashboardStatsAdmin)
admin.site.register(RevenueAnalytics, RevenueAnalyticsAdmin)
admin.site.register(BookingAnalytics, BookingAnalyticsAdmin)
admin.site.register(PropertyPerformance, PropertyPerformanceAdmin)
admin.site.register(UserActivity, UserActivityAdmin)
admin.site.register(SystemAlert, SystemAlertAdmin)
admin.site.register(DashboardWidget, DashboardWidgetAdmin)
admin.site.register(Report, ReportAdmin)
admin.site.register(NotificationPreference, NotificationPreferenceAdmin)


# Custom admin views for analytics
class AnalyticsAdminSite(admin.AdminSite):
    site_header = "Reserve at Ease Analytics"
    site_title = "Reserve at Ease Admin"
    index_title = "Analytics Dashboard"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('analytics/', self.admin_view(self.analytics_view), name='analytics'),
        ]
        return custom_urls + urls

    def analytics_view(self, request):
        # Calculate key metrics
        today = timezone.now().date()
        this_month = today.replace(day=1)

        context = {
            'title': 'Analytics Dashboard',
            'total_users': User.objects.count(),
            'total_properties': Property.objects.count(),
            'total_reservations': Reservation.objects.count(),
            'total_revenue': Reservation.objects.filter(
                payment_status='paid'
            ).aggregate(total=Sum('total_price'))['total'] or 0,
            'new_users_today': User.objects.filter(date_joined__date=today).count(),
            'new_properties_today': Property.objects.filter(created_at__date=today).count(),
            'reservations_today': Reservation.objects.filter(created_at__date=today).count(),
            'revenue_today': Reservation.objects.filter(
                payment_status='paid',
                created_at__date=today
            ).aggregate(total=Sum('total_price'))['total'] or 0,
            'monthly_revenue': Reservation.objects.filter(
                payment_status='paid',
                created_at__date__gte=this_month
            ).aggregate(total=Sum('total_price'))['total'] or 0,
            'avg_rating': Property.objects.aggregate(avg=Avg('rating'))['avg'] or 0,
            'pending_reservations': Reservation.objects.filter(status='pending').count(),
        }

        return self.render(request, 'admin/analytics.html', context)


# Create analytics admin site
analytics_admin = AnalyticsAdminSite(name='analytics_admin')

# Register models with analytics admin
analytics_admin.register(User, admin.ModelAdmin)
analytics_admin.register(Property, admin.ModelAdmin)
analytics_admin.register(Reservation, admin.ModelAdmin)
analytics_admin.register(Review, admin.ModelAdmin)
