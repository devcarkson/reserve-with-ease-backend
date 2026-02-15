from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from reservations.models import Reservation

from .models import PaymentMethod, MonthlyInvoice
from .serializers import (
    PaymentMethodSerializer, PaymentMethodCreateUpdateSerializer, 
    MonthlyInvoiceSerializer
)


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
        # Return payment methods based on owner type
        if self.request.user.role == 'owner':
            if self.request.user.owner_type == 'single':
                # Single owners see their multi-owner's payment method
                from properties.models import Property
                property_obj = Property.objects.filter(authorized_users=self.request.user).first()
                if property_obj and property_obj.owner:
                    return PaymentMethod.objects.filter(owner=property_obj.owner)
                return PaymentMethod.objects.none()
            else:
                # Multi-owners see their own payment methods
                return PaymentMethod.objects.filter(owner=self.request.user)
        return PaymentMethod.objects.none()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PaymentMethodCreateUpdateSerializer
        return PaymentMethodSerializer

    def create(self, request, *args, **kwargs):
        # Single owners cannot create payment methods
        if request.user.owner_type == 'single':
            return Response(
                {'error': 'Single owners cannot create payment methods. Please contact your property owner.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Delete existing payment method for this owner only
        PaymentMethod.objects.filter(owner=self.request.user).delete()

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        instance = serializer.save(owner=self.request.user)

        # Return full serialized data with details
        response_serializer = PaymentMethodSerializer(instance)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, *args, **kwargs):
        # Single owners cannot update payment methods - send notification to multi-owner
        if request.user.owner_type == 'single':
            try:
                from properties.models import Property
                from notifications.models import Notification
                
                property_obj = Property.objects.filter(authorized_users=request.user).first()
                if property_obj and property_obj.owner:
                    # Create notification for multi-owner
                    Notification.objects.create(
                        user=property_obj.owner,
                        title='Payment Method Update Request',
                        message=f'{request.user.first_name} {request.user.last_name} ({request.user.email}) attempted to update the payment method for {property_obj.name}. Please review and update if needed.',
                        notification_type='payment',
                        is_read=False
                    )
            except Exception as e:
                print(f"Error creating notification: {e}")
            
            return Response(
                {'error': 'Single owners cannot update payment methods. Your property owner has been notified of your request.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
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
        """Get the owner's payment method (or multi-owner's for single owners)"""
        try:
            if request.user.owner_type == 'single':
                # Single owners get their multi-owner's payment method
                from properties.models import Property
                property_obj = Property.objects.filter(authorized_users=request.user).first()
                if property_obj and property_obj.owner:
                    payment_method = PaymentMethod.objects.filter(owner=property_obj.owner, is_active=True).first()
                else:
                    payment_method = None
            else:
                # Multi-owners get their own payment method
                payment_method = PaymentMethod.objects.filter(owner=request.user, is_active=True).first()
            
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
@permission_classes([])
def get_owner_payment_method_view(request, owner_id):
    """Get the payment method for a specific owner"""
    print(f"DEBUG: Received owner_id: '{owner_id}' - looking for owner's payment method")

    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        # Get the owner user
        owner = User.objects.filter(id=owner_id, role='owner').first()
        if not owner:
            print(f"DEBUG: Owner with id {owner_id} not found")
            return Response(
                {'message': 'Owner not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get the owner's payment method
        payment_method = PaymentMethod.objects.filter(owner=owner, is_active=True).first()

        if payment_method:
            print(f"DEBUG: Found payment method: {payment_method.id} ({payment_method.payment_type}) for owner {owner.email}")
            serializer = PaymentMethodSerializer(payment_method)
            return Response(serializer.data)
        else:
            print(f"DEBUG: No active payment method found for owner {owner.email}")
            return Response(
                {'message': 'No payment method configured. Please contact the property owner.'},
                status=status.HTTP_404_NOT_FOUND
            )
    except Exception as e:
        print(f"DEBUG: Error retrieving payment method: {e}")
        import traceback
        traceback.print_exc()
        return Response(
            {'message': f'Error retrieving payment method: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_invoices_view(request):
    """Get monthly invoices for the authenticated owner"""
    try:
        if request.user.role != 'owner':
            return Response(
                {'message': 'Access denied. Only owners can view invoices.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get owner based on owner_type
        if request.user.owner_type == 'single':
            # Single owners see their multi-owner's invoices
            from properties.models import Property
            property_obj = Property.objects.filter(authorized_users=request.user).first()
            if property_obj and property_obj.owner:
                owner = property_obj.owner
            else:
                return Response([], status=status.HTTP_200_OK)
        else:
            # Multi-owners see their own invoices
            owner = request.user
        
        # Only return published invoices
        invoices = MonthlyInvoice.objects.filter(
            owner=owner,
            status='published'
        ).order_by('-month')
        
        serializer = MonthlyInvoiceSerializer(invoices, many=True)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'message': f'Error retrieving monthly invoices: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def monthly_invoice_detail_view(request, invoice_id):
    """Get detailed information for a specific monthly invoice"""
    try:
        if request.user.role != 'owner':
            return Response(
                {'message': 'Access denied. Only owners can view invoices.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get owner based on owner_type
        if request.user.owner_type == 'single':
            # Single owners see their multi-owner's invoices
            from properties.models import Property
            property_obj = Property.objects.filter(authorized_users=request.user).first()
            if property_obj and property_obj.owner:
                owner = property_obj.owner
            else:
                return Response(
                    {'message': 'Invoice not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        else:
            # Multi-owners see their own invoices
            owner = request.user
        
        # Get the invoice
        invoice = get_object_or_404(
            MonthlyInvoice,
            id=invoice_id,
            owner=owner,
            status='published'  # Only allow access to published invoices
        )
        
        serializer = MonthlyInvoiceSerializer(invoice)
        return Response(serializer.data)
        
    except Exception as e:
        return Response(
            {'message': f'Error retrieving invoice details: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
