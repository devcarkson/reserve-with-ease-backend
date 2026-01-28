from django.db import models
from django.contrib.auth import get_user_model
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings

User = get_user_model()


class EmailTemplate(models.Model):
    TEMPLATE_TYPE_CHOICES = [
        ('booking_confirmation', 'Booking Confirmation'),
        ('booking_cancellation', 'Booking Cancellation'),
        ('owner_booking_notification', 'Owner Booking Notification'),
        ('review_response', 'Review Response'),
        ('welcome', 'Welcome Email'),
        ('password_reset', 'Password Reset'),
        ('email_verification', 'Email Verification'),
    ]

    name = models.CharField(max_length=255)
    template_type = models.CharField(max_length=30, choices=TEMPLATE_TYPE_CHOICES)
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} ({self.template_type})"


class EmailNotification(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]

    recipient = models.EmailField()
    subject = models.CharField(max_length=255)
    html_content = models.TextField()
    text_content = models.TextField(blank=True)
    template = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Email to {self.recipient}: {self.subject}"

    def send(self):
        """Send the email notification"""
        try:
            send_mail(
                subject=self.subject,
                message=self.text_content,
                html_message=self.html_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[self.recipient],
                fail_silently=False,
            )
            self.status = 'sent'
            self.sent_at = models.DateTimeField(auto_now=True)
            self.save()
            return True
        except Exception as e:
            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                self.status = 'failed'
            self.error_message = str(e)
            self.save()
            return False


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('booking_confirmed', 'Booking Confirmed'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('payment_received', 'Payment Received'),
        ('review_received', 'Review Received'),
        ('message_received', 'Message Received'),
        ('system_alert', 'System Alert'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    action_url = models.URLField(blank=True)
    related_object_type = models.CharField(max_length=50, blank=True)
    related_object_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user.username}: {self.title}"

    def mark_as_read(self):
        from django.utils import timezone
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()