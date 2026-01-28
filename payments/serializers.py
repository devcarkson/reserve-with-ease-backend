from rest_framework import serializers
from .models import PaymentMethod


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