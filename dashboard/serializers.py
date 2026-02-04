from rest_framework import serializers
from .models import (
    UserDashboardStats, OwnerDashboardStats, AdminDashboardStats,
    RevenueAnalytics, BookingAnalytics, PropertyPerformance,
    UserActivity, SystemAlert, DashboardWidget, Report,
    NotificationPreference
)


class UserDashboardStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserDashboardStats
        fields = '__all__'


class OwnerDashboardStatsSerializer(serializers.ModelSerializer):
    completion_rate = serializers.SerializerMethodField()
    cancellation_rate = serializers.SerializerMethodField()
    
    class Meta:
        model = OwnerDashboardStats
        fields = '__all__'
    
    def get_completion_rate(self, obj):
        if obj.total_reservations > 0:
            return round((obj.completed_reservations / obj.total_reservations) * 100, 1)
        return 0
    
    def get_cancellation_rate(self, obj):
        if obj.total_reservations > 0:
            return round((obj.cancelled_reservations / obj.total_reservations) * 100, 1)
        return 0


class AdminDashboardStatsSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminDashboardStats
        fields = '__all__'


class RevenueAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RevenueAnalytics
        fields = '__all__'


class BookingAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingAnalytics
        fields = '__all__'


class PropertyPerformanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyPerformance
        fields = '__all__'


class UserActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserActivity
        fields = '__all__'


class SystemAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemAlert
        fields = '__all__'


class DashboardWidgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = DashboardWidget
        fields = '__all__'


class ReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = Report
        fields = '__all__'


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = '__all__'