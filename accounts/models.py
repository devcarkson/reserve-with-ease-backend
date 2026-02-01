from django.contrib.auth.models import AbstractUser
from django.db import models
from django_otp.models import Device
from django_otp.util import random_hex
import qrcode
import io
import base64


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
    # 2FA fields
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=32, blank=True, null=True)
    two_factor_backup_codes = models.JSONField(default=list, blank=True)
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
    
    def generate_2fa_secret(self):
        """Generate a new 2FA secret for the user"""
        import pyotp
        self.two_factor_secret = pyotp.random_base32()
        self.save()
        return self.two_factor_secret
    
    def get_2fa_qr_code(self, secret=None):
        """Generate QR code for Google Authenticator"""
        import pyotp
        import qrcode
        import io
        import base64
        
        if not secret:
            secret = self.two_factor_secret
        
        if not secret:
            return None
            
        # Create TOTP URI
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=self.email,
            issuer_name="ReserveWithEase"
        )
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_code_data = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{qr_code_data}"
    
    def verify_2fa_token(self, token):
        """Verify a 2FA token"""
        import pyotp
        
        if not self.two_factor_secret:
            return False
            
        totp = pyotp.TOTP(self.two_factor_secret)
        return totp.verify(token, valid_window=1)  # Allow 1 step tolerance
    
    def generate_backup_codes(self):
        """Generate backup codes for 2FA"""
        import secrets
        
        codes = []
        for _ in range(10):  # Generate 10 backup codes
            code = f"{secrets.randbelow(1000000):06d}"  # 6-digit codes
            codes.append(code)
        
        self.two_factor_backup_codes = codes
        self.save()
        return codes
    
    def verify_backup_code(self, code):
        """Verify and consume a backup code"""
        if code in self.two_factor_backup_codes:
            self.two_factor_backup_codes.remove(code)
            self.save()
            return True
        return False


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
