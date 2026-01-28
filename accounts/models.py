from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('owner', 'Owner'),
        ('admin', 'Admin'),
    ]
    OWNER_TYPE_CHOICES = [
        ('single', 'Single Owner'),
        ('multi', 'Multi Owner'),
    ]
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='user')
    status = models.CharField(
        max_length=10, 
        choices=[('active', 'Active'), ('suspended', 'Suspended')], 
        default='active'
    )
    owner_type = models.CharField(
        max_length=10, 
        choices=OWNER_TYPE_CHOICES, 
        default='', 
        blank=True,
        null=True
    )
    phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.username} ({self.role})"
    
    @property
    def is_owner(self):
        return self.role == 'owner'
    
    @property
    def is_admin_user(self):
        return self.role == 'admin'
    
    @property
    def is_regular_user(self):
        return self.role == 'user'


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(blank=True)
    company = models.CharField(max_length=255, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    nationality = models.CharField(max_length=100, blank=True)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    preferred_language = models.CharField(max_length=10, default='en')
    currency_preference = models.CharField(max_length=3, default='NGN')
    notification_preferences = models.JSONField(default=dict)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"


class EmailVerification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_verifications', null=True, blank=True)
    email = models.EmailField(null=True, blank=True)  # For invitations before user creation
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    invitation_type = models.CharField(max_length=20, default='verification', choices=[
        ('verification', 'Email Verification'),
        ('owner_invitation', 'Owner Invitation'),
    ])
    owner_type = models.CharField(max_length=10, blank=True, choices=[
        ('single', 'Single Owner'),
        ('multi', 'Multi Owner'),
    ])
    property_id = models.IntegerField(null=True, blank=True)
    
    def __str__(self):
        return f"Email verification for {self.user.username}"


class PasswordReset(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='password_resets')
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Password reset for {self.user.username}"
