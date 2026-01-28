from django.contrib import admin
from .models import (
    Reservation, Payment, Refund, Cancellation, BookingModification, 
    CheckIn, CheckOut, ReviewInvitation
)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    def formatted_price(self, obj):
        return f"₦{obj.total_price:,.0f}"
    formatted_price.short_description = 'Total Price'

    list_display = ('id', 'property_obj', 'room', 'user', 'guest_first_name', 'guest_last_name',
                   'check_in', 'check_out', 'guests', 'formatted_price', 'status', 'payment_status', 'created_at')
    list_filter = ('status', 'payment_status', 'property_obj', 'created_at', 'check_in', 'check_out')
    search_fields = ('id', 'guest_first_name', 'guest_last_name', 'guest_email', 'user__username',
                   'property_obj__name', 'room__name')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')

    fieldsets = (
        ('Basic Info', {
            'fields': ('property_obj', 'room', 'user', 'check_in', 'check_out', 'guests', 'total_price')
        }),
        ('Guest Information', {
            'fields': ('guest_first_name', 'guest_last_name', 'guest_email', 'guest_phone')
        }),
        ('Status', {
            'fields': ('status', 'payment_status')
        }),
        ('Payment Details', {
            'fields': ('payment_method', 'amount_paid', 'payment_date', 'collected_by', 'payment_notes', 
                       'payment_receipt', 'receipt_uploaded_at'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('special_requests', 'estimated_arrival_time', 'flight_details'),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Property owners can only see reservations for their properties
        return qs.filter(property_obj__owner=request.user)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'reservation', 'payment_type', 'payment_method', 'amount', 'status', 'transaction_id', 'created_at')
    list_filter = ('payment_type', 'payment_method', 'status', 'created_at')
    search_fields = ('reservation__id', 'transaction_id', 'amount')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(reservation__property_obj__owner=request.user)


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'amount', 'status', 'refund_id', 'processed_by', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('payment__reservation__id', 'refund_id', 'amount')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(payment__reservation__property_obj__owner=request.user)


@admin.register(Cancellation)
class CancellationAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'reason', 'refund_amount', 'cancellation_fee', 'processed_by', 'created_at')
    list_filter = ('reason', 'created_at')
    search_fields = ('reservation__id', 'reason_details')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(reservation__property_obj__owner=request.user)


@admin.register(BookingModification)
class BookingModificationAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'modification_type', 'modified_by', 'created_at')
    list_filter = ('modification_type', 'created_at')
    search_fields = ('reservation__id', 'reason', 'new_values')
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(reservation__property_obj__owner=request.user)


@admin.register(CheckIn)
class CheckInAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'actual_check_in_time', 'checked_in_by', 'id_document_verified', 'payment_collected', 'created_at')
    list_filter = ('id_document_verified', 'payment_collected', 'created_at')
    search_fields = ('reservation__id',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(reservation__property_obj__owner=request.user)


@admin.register(CheckOut)
class CheckOutAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'actual_check_out_time', 'checked_out_by', 'additional_charges', 'damage_charges', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('reservation__id',)
    ordering = ('-created_at',)
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(reservation__property_obj__owner=request.user)


@admin.register(ReviewInvitation)
class ReviewInvitationAdmin(admin.ModelAdmin):
    list_display = ('reservation', 'token', 'sent_at', 'opened_at', 'completed', 'created_at')
    list_filter = ('completed', 'sent_at', 'opened_at', 'created_at')
    search_fields = ('reservation__id', 'token')
    ordering = ('-created_at',)
    readonly_fields = ('token', 'created_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(reservation__property_obj__owner=request.user)
