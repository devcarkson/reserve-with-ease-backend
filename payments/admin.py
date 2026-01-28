from django.contrib import admin
from .models import PaymentMethod


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'owner', 'payment_type', 'is_active', 'is_verified',
        'created_at', 'updated_at'
    ]
    list_filter = ['payment_type', 'is_active', 'is_verified', 'created_at', 'updated_at']
    search_fields = ['owner__username', 'owner__email', 'account_name', 'bank_name']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('owner', 'payment_type', 'is_active', 'is_verified')
        }),
        ('Bank Transfer Details', {
            'fields': ('account_name', 'account_number', 'bank_name', 'routing_number'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('owner')

    def owner_username(self, obj):
        return obj.owner.username
    owner_username.short_description = 'Owner Username'

    def owner_email(self, obj):
        return obj.owner.email
    owner_email.short_description = 'Owner Email'
