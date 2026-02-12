from django.db import models
from django.contrib.auth import get_user_model
from properties.models import Property, Room

User = get_user_model()


class Reservation(models.Model):
    STATUS_CHOICES = [
        ('confirmed', 'Confirmed'),
        ('pending', 'Pending'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
        ('no-show', 'No Show'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('pay_now', 'Pay Now'),
        ('pay_on_arrival', 'Pay on Arrival'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('partially_paid', 'Partially Paid'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    ]
    
    property_obj = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reservations')
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='reservations', null=True, blank=True)
    room_category = models.ForeignKey('properties.RoomCategory', on_delete=models.CASCADE, related_name='reservations', null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reservations')
    check_in = models.DateField()
    check_out = models.DateField()
    guests = models.IntegerField()
    total_price = models.DecimalField(max_digits=12, decimal_places=2)
    original_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)  # Original price before discount
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # Discount percentage at time of booking
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Guest information
    guest_first_name = models.CharField(max_length=100)
    guest_last_name = models.CharField(max_length=100)
    guest_email = models.EmailField()
    guest_phone = models.CharField(max_length=20)
    
    # Payment information
    payment_method = models.CharField(max_length=15, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=15, choices=PAYMENT_STATUS_CHOICES, default='pending')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_date = models.DateTimeField(null=True, blank=True)
    collected_by = models.CharField(max_length=100, blank=True)
    payment_notes = models.TextField(blank=True)
    payment_receipt = models.ImageField(upload_to='payment_receipts/', blank=True, null=True)
    receipt_uploaded_at = models.DateTimeField(null=True, blank=True)
    
    # Additional information
    special_requests = models.TextField(blank=True)
    estimated_arrival_time = models.TimeField(null=True, blank=True)
    flight_details = models.TextField(blank=True)
    
    # Reference ID for user-friendly identification
    reference = models.CharField(max_length=20, unique=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reservation {self.id} - {self.property_obj.name}"
    
    @property
    def nights(self):
        return (self.check_out - self.check_in).days
    
    @property
    def is_paid(self):
        return self.payment_status == 'paid'
    
    @property
    def is_active(self):
        return self.status in ['confirmed', 'pending']
    
    @property
    def can_cancel(self):
        from django.utils import timezone
        return self.status in ['confirmed', 'pending'] and self.check_in > timezone.now().date()


class Payment(models.Model):
    PAYMENT_TYPE_CHOICES = [
        ('deposit', 'Deposit'),
        ('full_payment', 'Full Payment'),
        ('balance', 'Balance Payment'),
    ]
    PAYMENT_METHOD_CHOICES = [
        ('card', 'Credit/Debit Card'),
        ('bank_transfer', 'Bank Transfer'),
        ('cash', 'Cash'),
        ('mobile_money', 'Mobile Money'),
        ('paypal', 'PayPal'),
        ('stripe', 'Stripe'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='payments')
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPE_CHOICES)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    transaction_id = models.CharField(max_length=255, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Payment {self.id} - {self.reservation.id}"


class Refund(models.Model):
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Payment.STATUS_CHOICES, default='pending')
    refund_id = models.CharField(max_length=255, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Refund {self.id} - {self.payment.id}"


class Cancellation(models.Model):
    REASON_CHOICES = [
        ('guest_request', 'Guest Request'),
        ('property_issue', 'Property Issue'),
        ('force_majeure', 'Force Majeure'),
        ('payment_issue', 'Payment Issue'),
        ('other', 'Other'),
    ]
    
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='cancellation')
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    reason_details = models.TextField()
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cancellation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    processed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Cancellation for Reservation {self.reservation.id}"


class BookingModification(models.Model):
    MODIFICATION_TYPE_CHOICES = [
        ('date_change', 'Date Change'),
        ('guest_change', 'Guest Change'),
        ('room_change', 'Room Change'),
        ('cancellation', 'Cancellation'),
    ]
    
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='modifications')
    modification_type = models.CharField(max_length=20, choices=MODIFICATION_TYPE_CHOICES)
    old_values = models.JSONField(default=dict)
    new_values = models.JSONField(default=dict)
    reason = models.TextField(blank=True)
    modified_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Modification for Reservation {self.reservation.id}"


class CheckIn(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='checkin')
    actual_check_in_time = models.DateTimeField()
    checked_in_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    id_document_verified = models.BooleanField(default=False)
    payment_collected = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Check-in for Reservation {self.reservation.id}"


class CheckOut(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='checkout')
    actual_check_out_time = models.DateTimeField()
    checked_out_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    additional_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    damage_charges = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Check-out for Reservation {self.reservation.id}"


class ReviewInvitation(models.Model):
    reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='review_invitation')
    token = models.CharField(max_length=255, unique=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    opened_at = models.DateTimeField(null=True, blank=True)
    completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Review Invitation for Reservation {self.reservation.id}"
