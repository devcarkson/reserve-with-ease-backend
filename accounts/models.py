from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class User(AbstractUser):
    ROLE_CHOICES = (
        ('user', 'User'),
        ('owner', 'Owner'),
        ('admin', 'Admin'),
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('suspended', 'Suspended'),
    )
    OWNER_TYPE_CHOICES = (
        ('single', 'Single Owner'),
        ('multi', 'Multi Owner'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    owner_type = models.CharField(max_length=10, choices=OWNER_TYPE_CHOICES, default='multi', blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pics/', null=True, blank=True)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=128, blank=True, null=True)
    two_factor_backup_codes = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'user'
        verbose_name_plural = 'users'


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(max_length=10, default='en')
    currency_preference = models.CharField(max_length=3, default='NGN')
    notification_preferences = models.JSONField(default=dict)
    company = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class EmailVerification(models.Model):
    INVITATION_TYPE_CHOICES = (
        ('owner', 'Owner'),
        ('staff', 'Staff'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_verifications')
    token = models.CharField(max_length=255, unique=True)
    email = models.EmailField(blank=True)
    invitation_type = models.CharField(max_length=20, choices=INVITATION_TYPE_CHOICES, blank=True)
    owner_type = models.CharField(max_length=10, blank=True)
    property_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Email verification for {self.user.email}"


class PasswordReset(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='password_resets')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"Password reset for {self.user.email}"


class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlists')
    property_id = models.IntegerField()  # Store property ID to avoid circular import
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'property_id']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s wishlist - Property #{self.property_id}"
