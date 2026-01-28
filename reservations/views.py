from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum
from django.utils import timezone
from django.http import HttpResponse, Http404
from datetime import datetime
from properties.models import Property
from .models import Reservation, Payment, Cancellation, CheckIn, CheckOut
from .serializers import (
    ReservationSerializer, ReservationCreateSerializer, ReservationUpdateSerializer,
    ReservationListSerializer, OwnerReservationSerializer, PaymentCreateSerializer,
    CancellationCreateSerializer, CheckInCreateSerializer, CheckOutCreateSerializer,
    CancellationSerializer, PaymentSerializer, CheckInSerializer, CheckOutSerializer
)

User = get_user_model()


class IsReservationUser(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user or obj.property_obj.owner == request.user


class IsPropertyOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.property_obj.owner == request.user


class ReservationListCreateView(generics.ListCreateAPIView):
    serializer_class = ReservationListSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['status', 'payment_status', 'property_obj']
    ordering_fields = ['created_at', 'check_in', 'check_out', 'total_price']
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'owner':
            # Owners see reservations for their properties and properties they're authorized to manage
            return Reservation.objects.filter(
                Q(property_obj__owner=user) | Q(property_obj__authorized_users=user)
            ).distinct()
        else:
            # Users see their own reservations
            return Reservation.objects.filter(user=user)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return ReservationCreateSerializer
        return ReservationListSerializer


class ReservationDetailView(generics.RetrieveUpdateAPIView):
    queryset = Reservation.objects.all()
    permission_classes = [permissions.IsAuthenticated, IsReservationUser]

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return ReservationUpdateSerializer
        return OwnerReservationSerializer


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_reservation_view(request):
    """Create a new reservation with availability check"""
    serializer = ReservationCreateSerializer(data=request.data, context={'request': request})
    serializer.is_valid(raise_exception=True)

    reservation = serializer.save()
    print(f"Created reservation with ID: {reservation.id}")  # Debug log

    # Create review invitation
    try:
        from .models import ReviewInvitation
        from django.utils.crypto import get_random_string
        ReviewInvitation.objects.create(
            reservation=reservation,
            token=get_random_string(32)
        )
    except Exception as e:
        print(f"Warning: Failed to create review invitation: {e}")
        # Continue even if review invitation fails

    # Send notifications (with error handling)
    try:
        from notifications.utils import send_booking_notifications
        send_booking_notifications(reservation)
    except Exception as e:
        print(f"Warning: Failed to send booking notifications: {e}")
        # Continue even if notifications fail

    # Generate reservation reference ID
    import uuid
    reference_id = f"RWE{str(uuid.uuid4())[:7].upper()}"
    
    # Update reservation with reference ID
    reservation.reference = reference_id
    reservation.save()
    
    # Return both ID and reference ID
    return Response(
        {
            'id': reservation.id,
            'reference_id': reference_id
        },
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsReservationUser])
def cancel_reservation_view(request, reservation_id):
    """Cancel a reservation"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
    except Reservation.DoesNotExist:
        return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if not reservation.can_cancel:
        return Response({'error': 'Reservation cannot be cancelled'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = CancellationCreateSerializer(
        data=request.data,
        context={'reservation': reservation, 'request': request}
    )
    serializer.is_valid(raise_exception=True)
    cancellation = serializer.save()
    
    return Response({
        'message': 'Reservation cancelled successfully',
        'cancellation': CancellationSerializer(cancellation).data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsPropertyOwner])
def confirm_reservation_view(request, reservation_id):
    """Confirm a reservation (owner only)"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
    except Reservation.DoesNotExist:
        return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if reservation.status != 'pending':
        return Response({'error': 'Reservation cannot be confirmed'}, status=status.HTTP_400_BAD_REQUEST)
    
    reservation.status = 'confirmed'
    reservation.save()
    
    return Response({
        'message': 'Reservation confirmed successfully',
        'reservation': ReservationSerializer(reservation).data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsPropertyOwner])
def check_in_reservation_view(request, reservation_id):
    """Check in a guest (owner only)"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
    except Reservation.DoesNotExist:
        return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if reservation.status != 'confirmed':
        return Response({'error': 'Reservation must be confirmed to check in'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = CheckInCreateSerializer(
        data=request.data,
        context={'reservation': reservation, 'request': request}
    )
    serializer.is_valid(raise_exception=True)
    check_in = serializer.save()
    
    reservation.status = 'confirmed'  # Keep as confirmed, check-in is separate
    reservation.save()
    
    return Response({
        'message': 'Guest checked in successfully',
        'check_in': CheckInSerializer(check_in).data
    })


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsPropertyOwner])
def check_out_reservation_view(request, reservation_id):
    """Check out a guest (owner only)"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
    except Reservation.DoesNotExist:
        return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = CheckOutCreateSerializer(
        data=request.data,
        context={'reservation': reservation, 'request': request}
    )
    serializer.is_valid(raise_exception=True)
    check_out = serializer.save()
    
    return Response({
        'message': 'Guest checked out successfully',
        'check_out': CheckOutSerializer(check_out).data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def owner_reservations_view(request):
    """Get reservations for owner's properties and accessible properties"""
    if request.user.role != 'owner':
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    # Get optional property filter
    property_id = request.GET.get('property_id')

    # Base queryset based on owner type
    if request.user.owner_type == 'multi':
        # Multi-owners see reservations for properties they own, created, or are authorized to manage
        queryset = Reservation.objects.filter(
            Q(property_obj__owner=request.user) |
            Q(property_obj__created_by=request.user) |
            Q(property_obj__authorized_users=request.user)
        ).distinct()
    else:
        # Single owners see only their own properties
        queryset = Reservation.objects.filter(property_obj__owner=request.user)

    # Filter by specific property if provided
    if property_id:
        try:
            property_id = int(property_id)
            # For multi-owners, allow access to any property
            # For single-owners, verify ownership
            if request.user.owner_type != 'multi':
                from properties.models import Property
                Property.objects.get(id=property_id, owner=request.user)
            queryset = queryset.filter(property_obj_id=property_id)
        except (ValueError, Property.DoesNotExist):
            return Response({'error': 'Invalid property ID'}, status=status.HTTP_400_BAD_REQUEST)

    reservations = queryset
    serializer = OwnerReservationSerializer(reservations, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def reservation_calendar_view(request, property_id=None):
    """Get calendar view of reservations"""
    if property_id:
        # Check if user owns the property or is authorized to manage it
        try:
            property_obj = Property.objects.get(
                Q(id=property_id) & (Q(owner=request.user) | Q(authorized_users=request.user))
            )
        except Property.DoesNotExist:
            return Response({'error': 'Property not found or access denied'}, status=status.HTTP_404_NOT_FOUND)

        reservations = Reservation.objects.filter(property_obj=property_obj)
    else:
        # Get all reservations for owner's properties and authorized properties
        if request.user.role != 'owner':
            return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

        reservations = Reservation.objects.filter(
            Q(property_obj__owner=request.user) | Q(property_obj__authorized_users=request.user)
        ).distinct()
    
    # Format for calendar
    calendar_data = []
    for reservation in reservations:
        calendar_data.append({
            'id': reservation.id,
            'title': f"{reservation.guest_first_name} {reservation.guest_last_name}",
            'start': reservation.check_in,
            'end': reservation.check_out,
            'status': reservation.status,
            'property_name': reservation.property.name,
            'room_name': reservation.room.name,
            'guests': reservation.guests,
            'total_price': str(reservation.total_price)
        })
    
    return Response(calendar_data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsReservationUser])
def add_payment_view(request, reservation_id):
    """Add payment to reservation"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
    except Reservation.DoesNotExist:
        return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = PaymentCreateSerializer(
        data=request.data,
        context={'reservation_id': reservation_id}
    )
    serializer.is_valid(raise_exception=True)
    payment = serializer.save()

    # Refresh reservation to get updated payment relationships
    reservation.refresh_from_db()

    # Update reservation payment status
    total_paid = reservation.payments.aggregate(total=Sum('amount'))['total'] or 0

    if total_paid >= reservation.total_price:
        reservation.payment_status = 'paid'
        reservation.amount_paid = reservation.total_price
        # Auto-confirm reservation when payment status changes to paid
        if reservation.status == 'pending':
            reservation.status = 'confirmed'
    elif total_paid > 0:
        reservation.payment_status = 'partially_paid'
        reservation.amount_paid = total_paid
        # Auto-confirm reservation when payment status changes to partially_paid
        if reservation.status == 'pending':
            reservation.status = 'confirmed'

    reservation.save()
    
    return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def reservation_stats_view(request):
    """Get reservation statistics for user"""
    user = request.user
    try:
        if getattr(user, 'role', None) == 'owner':
            qs = Reservation.objects.filter(
                Q(property_obj__owner=user) | Q(property_obj__authorized_users=user)
            ).distinct()
        else:
            qs = Reservation.objects.filter(user=user)

        today = timezone.now().date()
        stats = {
            'total_reservations': qs.count(),
            'pending_reservations': qs.filter(status='pending').count(),
            'confirmed_reservations': qs.filter(status='confirmed').count(),
            'completed_reservations': qs.filter(status='completed').count(),
            'cancelled_reservations': qs.filter(status='cancelled').count(),
            'total_revenue': qs.filter(payment_status='paid').aggregate(total=Sum('total_price'))['total'] or 0,
            # check_in and check_out are DateFields; compare directly to date
            'upcoming_checkins': qs.filter(status='confirmed', check_in__gte=today).count(),
            'pending_checkouts': qs.filter(status='confirmed', check_out__gte=today).count(),
        }
        return Response(stats)
    except Exception as e:
        # Return a descriptive error for debugging instead of a 500 without context
        return Response({'error': f'Failed to compute stats: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsReservationUser])
def upload_payment_receipt_view(request, reservation_ref):
    """Upload payment receipt for a reservation"""
    print(f"Upload receipt request received for reservation {reservation_ref}")
    print(f"Request method: {request.method}")
    print(f"Request FILES: {request.FILES}")
    print(f"Request POST data: {request.POST}")
    print(f"User: {request.user}")

    try:
        reservation = Reservation.objects.get(reference=reservation_ref)
        print(f"Found reservation: {reservation.id} with reference: {reservation.reference}")
    except Reservation.DoesNotExist:
        print(f"Reservation {reservation_ref} not found")
        return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)

    receipt = request.FILES.get('receipt')
    if not receipt:
        print("No receipt file in request")
        return Response({'error': 'Receipt file is required'}, status=status.HTTP_400_BAD_REQUEST)

    print(f"Receipt file details: name={receipt.name}, size={receipt.size}, content_type={receipt.content_type}")

    # Update reservation with receipt
    try:
        # Check if media directory exists and is writable
        import os
        from django.conf import settings
        media_root = settings.MEDIA_ROOT
        print(f"Media root: {media_root}")
        
        if not os.path.exists(media_root):
            print(f"Media directory does not exist, creating: {media_root}")
            os.makedirs(media_root, exist_ok=True)
            print(f"Created media directory: {media_root}")
        else:
            print(f"Media directory exists: {media_root}")
            print(f"Media directory writable: {os.access(media_root, os.W_OK)}")
        
        # Create payment_receipts subdirectory
        receipt_dir = os.path.join(media_root, 'payment_receipts')
        if not os.path.exists(receipt_dir):
            print(f"Creating receipt directory: {receipt_dir}")
            os.makedirs(receipt_dir, exist_ok=True)
        
        print(f"Attempting to save receipt file: {receipt.name}, size: {receipt.size}")
        
        reservation.payment_receipt = receipt
        reservation.receipt_uploaded_at = timezone.now()
        reservation.save()
        
        print(f"Receipt saved successfully at: {reservation.payment_receipt.path}")
        print(f"Receipt URL: {reservation.payment_receipt.url}")
    except Exception as e:
        print(f"Error saving receipt: {e}")
        import traceback
        traceback.print_exc()
        return Response({'error': f'Failed to save receipt: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # Create notification for owner (with error handling)
    try:
        from notifications.utils import create_notification
        create_notification(
            user=reservation.property.owner,
            notification_type='payment_received',
            title='Payment Receipt Uploaded',
            message=f'{reservation.guest_first_name} {reservation.guest_last_name} has uploaded a payment receipt for their booking at {reservation.property.name}.',
            action_url=f'/owner/reservations/{reservation.id}',
            related_object=reservation
        )
        print("Notification created successfully")
    except Exception as e:
        print(f"Warning: Failed to create notification: {e}")
        # Continue even if notification fails

    response_data = {
        'message': 'Payment receipt uploaded successfully',
        'receipt_url': reservation.payment_receipt.url if reservation.payment_receipt else None
    }
    print(f"Returning response: {response_data}")
    return Response(response_data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated, IsPropertyOwner])
def approve_payment_view(request, reservation_id):
    """Approve payment receipt (owner only)"""
    try:
        reservation = Reservation.objects.get(id=reservation_id)
    except Reservation.DoesNotExist:
        return Response({'error': 'Reservation not found'}, status=status.HTTP_404_NOT_FOUND)

    if not reservation.payment_receipt:
        return Response({'error': 'No payment receipt uploaded'}, status=status.HTTP_400_BAD_REQUEST)

    # Update payment status
    reservation.payment_status = 'paid'
    reservation.amount_paid = reservation.total_price
    reservation.payment_date = timezone.now()
    reservation.collected_by = request.user.get_full_name() or request.user.username
    # Auto-confirm reservation when payment is approved
    if reservation.status == 'pending':
        reservation.status = 'confirmed'
    reservation.save()

    # Create notification for guest
    from notifications.utils import create_notification
    create_notification(
        user=reservation.user,
        notification_type='payment_received',
        title='Payment Approved',
        message=f'Your payment for the booking at {reservation.property.name} has been approved.',
        action_url=f'/user/reservations/{reservation.id}',
        related_object=reservation
    )

    return Response({
        'message': 'Payment approved successfully',
        'reservation': ReservationSerializer(reservation).data
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def check_availability_view(request):
    """Check availability for a property/room category combination"""
    property_id = request.GET.get('property_id')
    room_category_id = request.GET.get('room_category_id')
    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')
    guests = request.GET.get('guests')

    if not all([property_id, room_category_id, check_in, check_out, guests]):
        return Response(
            {'error': 'Missing required parameters: property_id, room_category_id, check_in, check_out, guests'},
            status=status.HTTP_400_BAD_REQUEST
        )

    try:
        from properties.models import Property, Room, RoomCategory
        property_obj = Property.objects.get(id=property_id)
        room_category = RoomCategory.objects.get(id=room_category_id, property=property_obj)

        # Parse dates
        check_in_date = datetime.strptime(check_in, '%Y-%m-%d').date()
        check_out_date = datetime.strptime(check_out, '%Y-%m-%d').date()
        guests_count = int(guests)

        # Validate dates
        if check_in_date >= check_out_date:
            return Response({'available': False, 'error': 'Check-out must be after check-in'})

        if check_in_date < timezone.now().date():
            return Response({'available': False, 'error': 'Check-in date cannot be in the past'})

        # Check room category capacity
        if guests_count > room_category.max_occupancy:
            return Response({
                'available': False,
                'error': f'Room category can only accommodate {room_category.max_occupancy} guests'
            })

        # Get all rooms in this category
        rooms = room_category.rooms.all()

        if not rooms.exists():
            return Response({'available': False, 'error': 'No rooms available in this category'})

        # Check if any room in the category is available
        available_rooms = []
        for room in rooms:
            # Check for conflicting reservations
            conflicting_reservations = Reservation.objects.filter(
                room=room,
                status__in=['confirmed', 'pending'],
                check_in__lt=check_out_date,
                check_out__gt=check_in_date
            )

            if not conflicting_reservations.exists():
                available_rooms.append(room)

        available = len(available_rooms) > 0

        response_data = {
            'available': available,
            'property_id': property_id,
            'room_category_id': room_category_id,
            'check_in': check_in,
            'check_out': check_out,
            'guests': guests_count,
            'available_rooms': len(available_rooms),
            'total_rooms': rooms.count()
        }

        # If available, include the first available room ID
        if available and available_rooms:
            response_data['available_room_id'] = available_rooms[0].id
            response_data['available_room_name'] = available_rooms[0].name

        return Response(response_data)

    except Property.DoesNotExist:
        return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)
    except RoomCategory.DoesNotExist:
        return Response({'error': 'Room category not found'}, status=status.HTTP_404_NOT_FOUND)
    except ValueError as e:
        return Response({'error': f'Invalid date format: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
