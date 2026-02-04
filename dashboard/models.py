from django.db import models
from django.contrib.auth import get_user_model
from properties.models import Property
from reservations.models import Reservation

User = get_user_model()


class UserDashboardStats(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dashboard_stats')
    total_reservations = models.IntegerField(default=0)
    upcoming_reservations = models.IntegerField(default=0)
    completed_reservations = models.IntegerField(default=0)
    cancelled_reservations = models.IntegerField(default=0)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    average_stay_duration = models.FloatField(default=0)
    favorite_property_type = models.CharField(max_length=50, blank=True)
    favorite_destination = models.CharField(max_length=100, blank=True)
    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Dashboard stats for {self.user.username}"


class OwnerDashboardStats(models.Model):
    owner = models.OneToOneField(User, on_delete=models.CASCADE, related_name='owner_dashboard_stats')
    total_properties = models.IntegerField(default=0)
    active_properties = models.IntegerField(default=0)
    total_reservations = models.IntegerField(default=0)
    upcoming_reservations = models.IntegerField(default=0)
    current_reservations = models.IntegerField(default=0)
    completed_reservations = models.IntegerField(default=0)
    cancelled_reservations = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    monthly_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    revenue_change_percentage = models.FloatField(default=0)
    reservation_change_percentage = models.FloatField(default=0)
    average_rating = models.FloatField(default=0)
    total_reviews = models.IntegerField(default=0)
    occupancy_rate = models.FloatField(default=0)
    average_daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    revenue_per_available_room = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Owner dashboard stats for {self.owner.username}"


class AdminDashboardStats(models.Model):
    date = models.DateField(unique=True)
    total_users = models.IntegerField(default=0)
    new_users = models.IntegerField(default=0)
    total_properties = models.IntegerField(default=0)
    new_properties = models.IntegerField(default=0)
    total_reservations = models.IntegerField(default=0)
    new_reservations = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    daily_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_reviews = models.IntegerField(default=0)
    new_reviews = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0)
    conversion_rate = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
    
    def __str__(self):
        return f"Admin stats for {self.date}"


class RevenueAnalytics(models.Model):
    PERIOD_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='revenue_analytics')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='revenue_analytics', null=True, blank=True)
    period = models.CharField(max_length=10, choices=PERIOD_CHOICES)
    date = models.DateField()
    revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    bookings = models.IntegerField(default=0)
    nights = models.IntegerField(default=0)
    average_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    occupancy_rate = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'property', 'period', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Revenue analytics for {self.user.username} - {self.date}"


class BookingAnalytics(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='booking_analytics')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='booking_analytics', null=True, blank=True)
    date = models.DateField()
    bookings = models.IntegerField(default=0)
    cancellations = models.IntegerField(default=0)
    modification_requests = models.IntegerField(default=0)
    conversion_rate = models.FloatField(default=0)
    average_booking_value = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    lead_time_days = models.FloatField(default=0)
    length_of_stay = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'property', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Booking analytics for {self.user.username} - {self.date}"


class PropertyPerformance(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='performance')
    date = models.DateField()
    views = models.IntegerField(default=0)
    unique_views = models.IntegerField(default=0)
    inquiries = models.IntegerField(default=0)
    bookings = models.IntegerField(default=0)
    conversion_rate = models.FloatField(default=0)
    average_rating = models.FloatField(default=0)
    total_reviews = models.IntegerField(default=0)
    search_ranking = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['property', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Performance for {self.property.name} on {self.date}"


class UserActivity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=50)
    description = models.TextField()
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username}: {self.activity_type}"


class SystemAlert(models.Model):
    ALERT_TYPE_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('success', 'Success'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    alert_type = models.CharField(max_length=10, choices=ALERT_TYPE_CHOICES)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    action_required = models.BooleanField(default=False)
    action_url = models.URLField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
    
    def __str__(self):
        return f"Alert: {self.title}"


class DashboardWidget(models.Model):
    WIDGET_TYPE_CHOICES = [
        ('stats', 'Statistics'),
        ('chart', 'Chart'),
        ('table', 'Table'),
        ('list', 'List'),
        ('calendar', 'Calendar'),
        ('map', 'Map'),
    ]
    
    name = models.CharField(max_length=100)
    widget_type = models.CharField(max_length=20, choices=WIDGET_TYPE_CHOICES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dashboard_widgets')
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    width = models.IntegerField(default=4)
    height = models.IntegerField(default=3)
    is_visible = models.BooleanField(default=True)
    config = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'name']
        ordering = ['position_y', 'position_x']
    
    def __str__(self):
        return f"Widget {self.name} for {self.user.username}"


class Report(models.Model):
    REPORT_TYPE_CHOICES = [
        ('revenue', 'Revenue Report'),
        ('occupancy', 'Occupancy Report'),
        ('booking', 'Booking Report'),
        ('guest', 'Guest Report'),
        ('property', 'Property Report'),
        ('review', 'Review Report'),
        ('financial', 'Financial Report'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    name = models.CharField(max_length=255)
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reports')
    parameters = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    file_path = models.CharField(max_length=500, blank=True)
    file_size = models.IntegerField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    generated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Report: {self.name} by {self.user.username}"


class NotificationPreference(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notification_preferences')
    notification_type = models.CharField(max_length=50)
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=False)
    push_enabled = models.BooleanField(default=True)
    frequency = models.CharField(max_length=20, default='immediate')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['user', 'notification_type']
    
    def __str__(self):
        return f"Notification preference for {self.user.username} - {self.notification_type}"
