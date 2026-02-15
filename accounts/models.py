from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
import pyotp
import secrets
import qrcode
import io
import base64


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
    
    def generate_2fa_secret(self):
        """Generate a new 2FA secret"""
        secret = pyotp.random_base32()
        self.two_factor_secret = secret
        self.save()
        return secret
    
    def get_2fa_qr_code(self, secret):
        """Generate QR code for 2FA setup"""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=self.email,
            issuer_name='ReserveWithEase'
        )
        
        # Generate QR code
        qr = qrcode.make(totp_uri)
        buffer = io.BytesIO()
        qr.save(buffer, format='PNG')
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        return f"data:image/png;base64,{qr_code_base64}"
    
    def generate_backup_codes(self):
        """Generate backup codes for 2FA"""
        backup_codes = []
        for _ in range(10):
            code = secrets.token_hex(4).upper()
            backup_codes.append(code)
        self.two_factor_backup_codes = backup_codes
        self.save()
        return backup_codes
    
    def verify_2fa_token(self, token):
        """Verify a 2FA token"""
        if not self.two_factor_secret:
            return False
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(token, valid_window=1)
    
    def verify_backup_code(self, code):
        """Verify a backup code"""
        if not self.two_factor_backup_codes or code not in self.two_factor_backup_codes:
            return False
        # Remove used backup code
        self.two_factor_backup_codes.remove(code)
        self.save()
        return True


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
    email = models.EmailField(blank=True, default='')
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


# Signals for automatic cleanup
from django.db.models.signals import post_delete
from django.dispatch import receiver


@receiver(post_delete, sender=User)
def cleanup_user_related_data(sender, instance, **kwargs):
    """Clean up orphaned tokens when a user is deleted"""
    try:
        # Clean up EmailVerification records
        deleted_ev = EmailVerification.objects.filter(user=instance).delete()
        if deleted_ev[0] > 0:
            print(f"Cleaned up {deleted_ev[0]} orphaned EmailVerification records")
        
        # Clean up PasswordReset records
        deleted_pr = PasswordReset.objects.filter(user=instance).delete()
        if deleted_pr[0] > 0:
            print(f"Cleaned up {deleted_pr[0]} orphaned PasswordReset records")
        
        # Clean up Wishlist records
        deleted_wl = Wishlist.objects.filter(user=instance).delete()
        if deleted_wl[0] > 0:
            print(f"Cleaned up {deleted_wl[0]} orphaned Wishlist records")
            
    except Exception as e:
        print(f"Error cleaning up user-related data: {e}")
