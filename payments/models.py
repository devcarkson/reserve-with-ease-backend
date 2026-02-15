from django.db import models
from django.conf import settings
from django.db.models import Sum, Q
from decimal import Decimal
from datetime import datetime, date
from django.utils import timezone


class MonthlyInvoice(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('paid', 'Paid'),
    ]
    
    invoice_number = models.CharField(max_length=50, unique=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='monthly_invoices')
    month = models.DateField()  # First day of the month
    period_start = models.DateField()
    period_end = models.DateField()
    total_reservations = models.IntegerField(default=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    issue_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='published_invoices'
    )
    paid_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-month']
        unique_together = ['owner', 'month']
    
    def __str__(self):
        return f"Invoice {self.id} - {self.owner.username} - {self.month.strftime('%B %Y')}"
    
    @property
    def month_display(self):
        if self.month:
            return self.month.strftime('%B %Y')
        return 'N/A'
    
    @property
    def period_display(self):
        if self.period_start and self.period_end:
            return f"{self.period_start.strftime('%Y-%m-%d')} to {self.period_end.strftime('%Y-%m-%d')}"
        return 'N/A'
    
    def calculate_totals(self):
        """Calculate invoice totals from paid reservations"""
        from reservations.models import Reservation
        
        # Get all paid reservations for this owner within the period
        reservations = Reservation.objects.filter(
            property_obj__owner=self.owner,
            payment_status='paid',
            payment_date__gte=self.period_start,
            payment_date__lte=self.period_end
        )
        
        # Calculate totals
        self.total_reservations = reservations.count()
        self.subtotal = reservations.aggregate(
            total=Sum('amount_paid')
        )['total'] or Decimal('0')
        
        # Calculate VAT (7.5%)
        self.vat_amount = self.subtotal * Decimal('0.075')
        self.total_amount = self.subtotal + self.vat_amount
        
        return reservations
    
    def get_reservations(self):
        """Get all reservations included in this invoice"""
        from reservations.models import Reservation
        
        return Reservation.objects.filter(
            property_obj__owner=self.owner,
            payment_status='paid',
            payment_date__gte=self.period_start,
            payment_date__lte=self.period_end
        ).select_related('property_obj').order_by('payment_date')


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
