from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from reservations.models import Reservation

from .models import PaymentMethod
from .serializers import PaymentMethodSerializer, PaymentMethodCreateUpdateSerializer


class IsAnyOwnerPermission:
    """Custom permission to only allow any owner to access payment methods"""

    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'owner'

    def has_object_permission(self, request, view, obj):
        return request.user.role == 'owner'


class PaymentMethodViewSet(viewsets.ModelViewSet):
    serializer_class = PaymentMethodSerializer
    permission_classes = [IsAuthenticated, IsAnyOwnerPermission]

    def get_queryset(self):
        # Return all payment methods for owners (they can manage the global one)
        if self.request.user.role == 'owner':
            return PaymentMethod.objects.all()
        return PaymentMethod.objects.none()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PaymentMethodCreateUpdateSerializer
        return PaymentMethodSerializer

    def create(self, request, *args, **kwargs):
        # For global payment method: delete all existing payment methods first
        PaymentMethod.objects.all().delete()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(owner=self.request.user)

        # Return full serialized data with details
        response_serializer = PaymentMethodSerializer(instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save()

        # Return full serialized data with details
        response_serializer = PaymentMethodSerializer(instance)
        return Response(response_serializer.data)

    @action(detail=False, methods=['get'])
    def my_payment_method(self, request):
        """Get the global payment method (for owners to manage)"""
        try:
            # Return the active global payment method
            payment_method = PaymentMethod.objects.filter(is_active=True).first()
            if payment_method:
                serializer = self.get_serializer(payment_method)
                return Response(serializer.data)
            else:
                return Response(
                    {'message': 'No payment method configured'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            return Response(
                {'message': 'Error retrieving payment method'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def earnings_summary(self, request):
        """Get total earnings from paid reservations"""
        try:
            paid_reservations = Reservation.objects.filter(
                property_obj__owner=request.user,
                payment_status='paid'
            )
            total_earnings = sum(float(r.amount_paid or r.total_price) for r in paid_reservations)
            return Response({'total_earnings': total_earnings})
        except Exception as e:
            return Response(
                {'message': f'Error calculating earnings: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def payment_history(self, request):
        """Get payment history for the authenticated owner from reservations"""
        try:
            # Get all reservations for properties owned by this user that have payments
            reservations = Reservation.objects.filter(
                property_obj__owner=request.user
            ).select_related('property_obj').order_by('-payment_date', '-created_at')
            
            # Transform to payment history format
            payment_history = []
            for reservation in reservations:
                # Map payment status to display status
                status_mapping = {
                    'paid': 'completed',
                    'partially_paid': 'pending',
                    'pending': 'pending',
                    'failed': 'failed',
                    'refunded': 'refunded'
                }
                
                # Map payment method to display method
                method_mapping = {
                    'pay_now': 'Bank Transfer',
                    'pay_on_arrival': 'Cash'
                }
                
                payment_history.append({
                    'id': f'P{reservation.id:03d}',
                    'amount': float(reservation.amount_paid or reservation.total_price),
                    'status': status_mapping.get(reservation.payment_status, reservation.payment_status),
                    'date': (reservation.payment_date or reservation.created_at).strftime('%Y-%m-%d'),
                    'method': method_mapping.get(reservation.payment_method, 'Bank Transfer'),
                    'reference': f'TXN-{(reservation.payment_date or reservation.created_at).strftime("%Y-%m")}-{reservation.id:03d}',
                    'reservation_id': reservation.reference or f'BK{reservation.id:03d}',
                    'guest_name': f'{reservation.guest_first_name} {reservation.guest_last_name}',
                    'property_name': reservation.property_obj.name
                })
            
            return Response(payment_history)
        except Exception as e:
            return Response(
                {'message': f'Error retrieving payment history: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_owner_payment_method_view(request, owner_id):
    """Get the global payment method for payment display (any owner can set/manage it)"""
    print(f"DEBUG: Received owner_id: '{owner_id}' - looking for global payment method")

    # Look for any active payment method in the system (global payment method)
    try:
        payment_method = PaymentMethod.objects.filter(is_active=True).first()

        if payment_method:
            print(f"DEBUG: Found global active payment method: {payment_method.id} ({payment_method.payment_type}) owned by {payment_method.owner.email}")
            serializer = PaymentMethodSerializer(payment_method)
            return Response(serializer.data)
        else:
            print(f"DEBUG: No active payment methods found in the system")
            return Response(
                {'message': 'No payment method configured. Please contact support.'},
                status=status.HTTP_404_NOT_FOUND
            )
    except Exception as e:
        print(f"DEBUG: Error retrieving global payment method: {e}")
        return Response(
            {'message': 'Error retrieving payment method'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    @action(detail=False, methods=['post'])
    def set_active(self, request):
        """Set a payment method as active (global)"""
        payment_method_id = request.data.get('id')
        if not payment_method_id:
            return Response(
                {'error': 'Payment method ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            payment_method = PaymentMethod.objects.get(id=payment_method_id)
            # Deactivate all other payment methods (global)
            PaymentMethod.objects.all().update(is_active=False)
            # Activate the selected one
            payment_method.is_active = True
            payment_method.save()

            serializer = self.get_serializer(payment_method)
            return Response(serializer.data)
        except PaymentMethod.DoesNotExist:
            return Response(
                {'error': 'Payment method not found'},
                status=status.HTTP_404_NOT_FOUND
            )
