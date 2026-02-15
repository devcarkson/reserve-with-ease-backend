from rest_framework import serializers
from .models import PaymentMethod, MonthlyInvoice


class ReservationSerializer(serializers.Serializer):
    """Serializer for reservation data in invoices"""
    id = serializers.CharField(source='reference')
    guest_name = serializers.SerializerMethodField()
    check_in = serializers.DateField()
    check_out = serializers.DateField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, source='amount_paid')
    status = serializers.CharField()
    property_name = serializers.CharField(source='property_obj.name')
    
    def get_guest_name(self, obj):
        return f"{obj.guest_first_name} {obj.guest_last_name}"


class MonthlyInvoiceSerializer(serializers.ModelSerializer):
    month_display = serializers.ReadOnlyField()
    period_display = serializers.ReadOnlyField()
    reservations = serializers.SerializerMethodField()
    
    class Meta:
        model = MonthlyInvoice
        fields = [
            'id', 'owner', 'month', 'month_display', 'period_start', 'period_end',
            'period_display', 'total_reservations', 'subtotal', 'vat_amount',
            'total_amount', 'status', 'issue_date', 'due_date', 'published_at', 'paid_date',
            'reservations'
        ]
        read_only_fields = ['id', 'issue_date', 'due_date', 'published_at', 'paid_date']
    
    def get_reservations(self, obj):
        reservations = obj.get_reservations()
        return ReservationSerializer(reservations, many=True).data


class PaymentMethodSerializer(serializers.ModelSerializer):
    details = serializers.SerializerMethodField()

    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'payment_type', 'name', 'details', 'is_active', 'is_verified',
            'created_at', 'updated_at', 'account_name', 'account_number',
            'bank_name', 'routing_number', 'mobile_provider', 'mobile_number',
            'wallet_email', 'wallet_id'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_verified']

    def get_details(self, obj):
        return obj.details

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

    def validate(self, data):
        payment_type = data.get('payment_type', self.instance.payment_type if self.instance else 'bank_transfer')

        # Validate required fields based on payment type
        if payment_type == 'bank_transfer':
            required_fields = ['account_name', 'account_number', 'bank_name']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError({field: f"This field is required for {payment_type}"})
        elif payment_type == 'mobile_money':
            if not data.get('mobile_number'):
                raise serializers.ValidationError({'mobile_number': f"This field is required for {payment_type}"})
        elif payment_type in ['paypal', 'stripe']:
            if not data.get('wallet_email'):
                raise serializers.ValidationError({'wallet_email': f"This field is required for {payment_type}"})

        return data


class PaymentMethodCreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = [
            'payment_type', 'name', 'account_name', 'account_number',
            'bank_name', 'routing_number', 'mobile_provider', 'mobile_number',
            'wallet_email', 'wallet_id', 'is_active'
        ]

    def validate(self, data):
        payment_type = data.get('payment_type', self.instance.payment_type if self.instance else 'bank_transfer')

        # Validate required fields based on payment type
        if payment_type == 'bank_transfer':
            required_fields = ['account_name', 'account_number', 'bank_name']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError({field: f"This field is required for {payment_type}"})
        elif payment_type == 'mobile_money':
            if not data.get('mobile_number'):
                raise serializers.ValidationError({'mobile_number': f"This field is required for {payment_type}"})
        elif payment_type in ['paypal', 'stripe']:
            if not data.get('wallet_email'):
                raise serializers.ValidationError({'wallet_email': f"This field is required for {payment_type}"})

        return data
