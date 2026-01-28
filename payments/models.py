from django.db import models
from django.conf import settings


class PaymentMethod(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('bank_transfer', 'Bank Transfer'),
        ('mobile_money', 'Mobile Money'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
    ]

    owner = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_method')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES, default='bank_transfer')
    name = models.CharField(max_length=100, help_text="Display name for this payment method")

    # Bank Transfer fields
    account_name = models.CharField(max_length=100, blank=True)
    account_number = models.CharField(max_length=50, blank=True)
    bank_name = models.CharField(max_length=100, blank=True)
    routing_number = models.CharField(max_length=50, blank=True)

    # Mobile Money fields
    mobile_provider = models.CharField(max_length=50, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)

    # Digital Wallet fields
    wallet_email = models.EmailField(blank=True)
    wallet_id = models.CharField(max_length=100, blank=True)

    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.owner.username}'s {self.name}"

    @property
    def masked_account_number(self):
        """Return masked account number for security"""
        if self.account_number and len(self.account_number) > 4:
            return f"****{self.account_number[-4:]}"
        return self.account_number

    @property
    def details(self):
        """Return payment method details based on type"""
        if self.payment_type == 'bank_transfer':
            return {
                'accountName': self.account_name,
                'accountNumber': self.masked_account_number,
                'bankName': self.bank_name,
                'routingNumber': self.routing_number,
            }
        elif self.payment_type == 'mobile_money':
            return {
                'provider': self.mobile_provider,
                'number': self.mobile_number,
            }
        elif self.payment_type in ['paypal', 'stripe']:
            return {
                'email': self.wallet_email,
                'walletId': self.wallet_id,
            }
        return {}
