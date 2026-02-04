from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Sum, Count, Avg, Q
from django.utils import timezone
from datetime import timedelta
from properties.models import Property
from reservations.models import Reservation
from reviews.models import Review
from accounts.models import User
from .models import (
    UserDashboardStats, OwnerDashboardStats, AdminDashboardStats,
    RevenueAnalytics, BookingAnalytics, PropertyPerformance,
    UserActivity, SystemAlert
)
from .serializers import (
    UserDashboardStatsSerializer, OwnerDashboardStatsSerializer,
    AdminDashboardStatsSerializer, UserActivitySerializer,
    SystemAlertSerializer
)


class IsAdminUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'admin'


class IsOwnerUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.role == 'owner'


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_dashboard_view(request):
    """Get dashboard stats for regular user"""
    user = request.user

    # Get or create user dashboard stats
    stats, created = UserDashboardStats.objects.get_or_create(user=user)

    # Update stats with real data
    reservations = Reservation.objects.filter(user=user)

    stats.total_reservations = reservations.count()
    stats.upcoming_reservations = reservations.filter(
        status__in=['confirmed', 'pending'],
        check_in__gte=timezone.now().date()
    ).count()
    stats.completed_reservations = reservations.filter(status='completed').count()
    stats.cancelled_reservations = reservations.filter(status='cancelled').count()
    stats.total_spent = reservations.filter(
        payment_status='paid'
    ).aggregate(total=Sum('total_price'))['total'] or 0

    # Calculate average stay duration
    completed_reservations = reservations.filter(status='completed')
    if completed_reservations.exists():
        total_nights = sum((r.check_out - r.check_in).days for r in completed_reservations)
        stats.average_stay_duration = total_nights / completed_reservations.count()
    else:
        stats.average_stay_duration = 0

    # Favorite property type and destination
    favorite_property = reservations.values('property__type').annotate(
        count=Count('property__type')
    ).order_by('-count').first()

    if favorite_property:
        stats.favorite_property_type = favorite_property['property__type']

    favorite_destination = reservations.values('property__city').annotate(
        count=Count('property__city')
    ).order_by('-count').first()

    if favorite_destination:
        stats.favorite_destination = favorite_destination['property__city']

    stats.last_login = user.last_login
    stats.save()

    serializer = UserDashboardStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def owner_dashboard_view(request):
    """Get dashboard stats for property owner"""
    user = request.user
    
    # Check if user is an owner
    if not hasattr(user, 'role') or user.role != 'owner':
        return Response({'error': 'Access denied - not an owner'}, status=status.HTTP_403_FORBIDDEN)

    try:
        # Force refresh by deleting existing stats
        OwnerDashboardStats.objects.filter(owner=user).delete()
        
        # Create new stats
        stats = OwnerDashboardStats(owner=user)

        # Update stats with real data - use same filtering as reservations API
        properties = Property.objects.filter(owner=user)
        
        # Use same filtering logic as owner_reservations_view
        if getattr(user, 'owner_type', None) == 'multi':
            # Multi-owners see reservations for properties they own, created, or are authorized to manage
            reservations = Reservation.objects.filter(
                Q(property_obj__owner=user) |
                Q(property_obj__created_by=user) |
                Q(property_obj__authorized_users=user)
            ).distinct()
        else:
            # Single owners see only their own properties
            reservations = Reservation.objects.filter(property_obj__owner=user)

        stats.total_properties = properties.count()
        stats.active_properties = properties.filter(status='active').count()
        stats.total_reservations = reservations.count()
        stats.current_reservations = reservations.filter(
            status='confirmed',
            check_in__lte=timezone.now().date(),
            check_out__gte=timezone.now().date()
        ).count()
        stats.completed_reservations = reservations.filter(status='completed').count()
        stats.cancelled_reservations = reservations.filter(status='cancelled').count()
        stats.upcoming_reservations = reservations.filter(
            status__in=['confirmed', 'pending']
        ).count()
        
        # Calculate occupancy rate based on completed reservations
        completed_reservations = reservations.filter(status='completed')
        if completed_reservations.exists() and reservations.count() > 0:
            occupancy_calc = (completed_reservations.count() / reservations.count()) * 100
            stats.occupancy_rate = round(occupancy_calc, 1)
        else:
            stats.occupancy_rate = 0
        
        # Debug: Check what statuses exist
        all_statuses = list(reservations.values_list('status', flat=True))
        import logging
        logger = logging.getLogger('django')
        logger.error(f"Dashboard Debug - All reservation statuses: {all_statuses}")
        logger.error(f"Dashboard Debug - Total reservations: {reservations.count()}")
        logger.error(f"Dashboard Debug - Completed reservations: {stats.completed_reservations}")
        logger.error(f"Dashboard Debug - Upcoming reservations: {stats.upcoming_reservations}")
        logger.error(f"Dashboard Debug - User owner_type: {getattr(user, 'owner_type', None)}")
        
        # Calculate revenue safely
        paid_reservations = reservations.filter(payment_status='paid')
        total_revenue = paid_reservations.aggregate(total=Sum('total_price'))['total']
        stats.total_revenue = total_revenue if total_revenue is not None else 0
        
        # Debug revenue calculation
        logger.error(f"Revenue Debug - Paid reservations count: {paid_reservations.count()}")
        logger.error(f"Revenue Debug - Total revenue: {stats.total_revenue}")
        if paid_reservations.exists():
            for res in paid_reservations:
                logger.error(f"Revenue Debug - Reservation {res.id}: NGN{res.total_price} (status: {res.payment_status})")

        # Monthly revenue (last 30 days)
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        monthly_revenue = reservations.filter(
            payment_status='paid',
            created_at__date__gte=thirty_days_ago
        ).aggregate(total=Sum('total_price'))['total']
        stats.monthly_revenue = monthly_revenue if monthly_revenue is not None else 0

        # Average rating
        avg_rating = properties.aggregate(avg_rating=Avg('rating'))['avg_rating']
        stats.average_rating = avg_rating if avg_rating else 0

        # Total reviews
        stats.total_reviews = Review.objects.filter(property_obj__owner=user).count()

        # Average daily rate
        paid_reservations = reservations.filter(payment_status='paid')
        if paid_reservations.exists():
            total_revenue_calc = paid_reservations.aggregate(
                total=Sum('total_price')
            )['total'] or 0
            total_nights = sum((r.check_out - r.check_in).days for r in paid_reservations if r.check_out and r.check_in)
            stats.average_daily_rate = total_revenue_calc / total_nights if total_nights > 0 else 0
        else:
            stats.average_daily_rate = 0

        stats.save()

        # Debug: Check final stats before serialization
        logger.error(f"Dashboard Debug - Final stats before serialization:")
        logger.error(f"  total_reservations: {stats.total_reservations}")
        logger.error(f"  completed_reservations: {stats.completed_reservations}")
        logger.error(f"  upcoming_reservations: {stats.upcoming_reservations}")
        logger.error(f"  occupancy_rate: {stats.occupancy_rate}")

        serializer = OwnerDashboardStatsSerializer(stats)
        
        # Debug: Print actual serialized data
        import logging
        logger = logging.getLogger('django')
        logger.error(f"Serialized response data: {serializer.data}")
        
        return Response(serializer.data)
    
    except Exception as e:
        # Log the error for debugging
        import traceback
        import logging
        logger = logging.getLogger('django')
        logger.error(f"Dashboard EXCEPTION for user {user.id}: {str(e)}")
        logger.error(f"Dashboard EXCEPTION traceback: {traceback.format_exc()}")
        print(f"Dashboard error for user {user.id}: {str(e)}")
        print(traceback.format_exc())
        
        # Return basic stats even if there's an error
        basic_stats = {
            'total_properties': Property.objects.filter(owner=user).count(),
            'active_properties': Property.objects.filter(owner=user, status='active').count(),
            'total_reservations': Reservation.objects.filter(property_obj__owner=user).count(),
            'upcoming_reservations': 0,
            'current_reservations': 0,
            'completed_reservations': 0,
            'cancelled_reservations': 0,
            'total_revenue': 0,
            'monthly_revenue': 0,
            'average_rating': 0,
            'total_reviews': 0,
            'occupancy_rate': 50.0,  # Set to 50% for testing
            'average_daily_rate': 0
        }
        return Response(basic_stats)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsAdminUser])
def admin_dashboard_view(request):
    """Get dashboard stats for admin"""
    # Get or create admin dashboard stats for today
    today = timezone.now().date()
    stats, created = AdminDashboardStats.objects.get_or_create(date=today)

    # Update stats with real data
    stats.total_users = User.objects.count()
    stats.new_users = User.objects.filter(
        date_joined__date=today
    ).count()

    stats.total_properties = Property.objects.count()
    stats.new_properties = Property.objects.filter(
        created_at__date=today
    ).count()

    stats.total_reservations = Reservation.objects.count()
    stats.new_reservations = Reservation.objects.filter(
        created_at__date=today
    ).count()

    stats.total_revenue = Reservation.objects.filter(
        payment_status='paid'
    ).aggregate(total=Sum('total_price'))['total'] or 0

    stats.daily_revenue = Reservation.objects.filter(
        payment_status='paid',
        created_at__date=today
    ).aggregate(total=Sum('total_price'))['total'] or 0

    stats.total_reviews = Review.objects.count()
    stats.new_reviews = Review.objects.filter(
        created_at__date=today
    ).count()

    avg_rating = Property.objects.aggregate(avg_rating=Avg('rating'))['avg_rating']
    stats.average_rating = avg_rating if avg_rating else 0

    # Conversion rate (simplified - reservations per property view)
    # This would need actual view tracking to be accurate
    stats.conversion_rate = 0  # Placeholder

    stats.save()

    serializer = AdminDashboardStatsSerializer(stats)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def user_activity_view(request):
    """Get recent user activity"""
    activities = UserActivity.objects.filter(user=request.user)[:20]
    serializer = UserActivitySerializer(activities, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def system_alerts_view(request):
    """Get system alerts for user"""
    alerts = SystemAlert.objects.filter(
        Q(user=request.user) | Q(user__isnull=True)
    ).filter(is_read=False)[:10]
    serializer = SystemAlertSerializer(alerts, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_alert_read_view(request, alert_id):
    """Mark system alert as read"""
    try:
        alert = SystemAlert.objects.get(id=alert_id, user=request.user)
        alert.is_read = True
        alert.save()
        return Response({'message': 'Alert marked as read'})
    except SystemAlert.DoesNotExist:
        return Response({'error': 'Alert not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsOwnerUser])
def performance_overview_view(request):
    """Get performance overview for the current owner"""
    owner = request.user
    
    # Get owner's properties
    properties = Property.objects.filter(owner=owner)
    
    # Get all reservations for owner's properties
    reservations = Reservation.objects.filter(property_obj__owner=owner)
    
    # Calculate performance metrics
    total_revenue = reservations.filter(payment_status='paid').aggregate(
        total=Sum('total_price')
    )['total'] or 0
    
    # Monthly revenue (last 30 days)
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    monthly_revenue = reservations.filter(
        payment_status='paid',
        created_at__date__gte=thirty_days_ago
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    # Booking trends (last 6 months)
    six_months_ago = timezone.now().date() - timedelta(days=180)
    monthly_bookings = []
    for i in range(6):
        month_start = timezone.now().date().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        booking_count = reservations.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        ).count()
        
        monthly_bookings.append({
            'month': month_start.strftime('%b'),
            'bookings': booking_count
        })
    
    monthly_bookings.reverse()  # Show oldest to newest
    
    # Occupancy rate - based on actual room capacity
    from properties.models import Room
    
    # Get all rooms for owner's properties
    owner_rooms = Room.objects.filter(property__owner=owner)
    total_rooms = owner_rooms.count()
    
    # Calculate occupancy for last 30 days
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    active_reservations = reservations.filter(
        status__in=['confirmed', 'completed'],
        check_out__gte=thirty_days_ago
    )
    
    # Calculate total nights actually booked in the last 30 days
    total_nights_booked = 0
    for r in active_reservations:
        if r.check_out and r.check_in:
            # Only count nights within the 30-day period
            period_start = max(r.check_in, thirty_days_ago)
            period_end = min(r.check_out, timezone.now().date())
            if period_end > period_start:
                nights = (period_end - period_start).days
                total_nights_booked += nights
    
    # Calculate total available room nights (rooms × 30 days)
    total_available_nights = total_rooms * 30
    
    # Calculate occupancy rate
    occupancy_rate = (total_nights_booked / total_available_nights * 100) if total_available_nights > 0 else 0
    
    # Average daily rate
    paid_reservations = reservations.filter(payment_status='paid')
    total_nights = sum(
        (r.check_out - r.check_in).days 
        for r in paid_reservations 
        if r.check_out and r.check_in
    )
    avg_daily_rate = total_revenue / total_nights if total_nights > 0 else 0
    
    # Response rate and time (mock data for now)
    response_rate = 95.0  # Placeholder
    avg_response_time = 2.5  # hours, placeholder
    
    performance_data = {
        'totalRevenue': total_revenue,
        'monthlyRevenue': monthly_revenue,
        'occupancyRate': round(occupancy_rate, 1),
        'averageDailyRate': round(avg_daily_rate, 2),
        'responseRate': response_rate,
        'averageResponseTime': avg_response_time,
        'bookingTrends': monthly_bookings,
        'totalProperties': properties.count(),
        'activeProperties': properties.filter(status='active').count(),
        'totalReservations': reservations.count(),
        'completedReservations': reservations.filter(status='completed').count()
    }
    
    return Response(performance_data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated, IsOwnerUser])
def reservation_performance_view(request):
    """Get detailed reservation performance for the current owner"""
    owner = request.user
    
    # Get owner's properties
    properties = Property.objects.filter(owner=owner)
    
    # Get all reservations for owner's properties
    reservations = Reservation.objects.filter(property_obj__owner=owner)
    
    # Reservation status breakdown
    status_breakdown = {}
    for status in ['pending', 'confirmed', 'cancelled', 'completed', 'no_show']:
        count = reservations.filter(status=status).count()
        if count > 0:
            status_breakdown[status] = count
    
    # Monthly booking trends (last 12 months)
    twelve_months_ago = timezone.now().date() - timedelta(days=365)
    monthly_trends = []
    
    for i in range(12):
        month_start = timezone.now().date().replace(day=1) - timedelta(days=30*i)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        month_reservations = reservations.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        )
        
        monthly_trends.append({
            'month': month_start.strftime('%b %Y'),
            'total': month_reservations.count(),
            'confirmed': month_reservations.filter(status='confirmed').count(),
            'cancelled': month_reservations.filter(status='cancelled').count(),
            'revenue': month_reservations.filter(payment_status='paid').aggregate(
                total=Sum('total_price')
            )['total'] or 0
        })
    
    monthly_trends.reverse()  # Show oldest to newest
    
    # Property performance
    property_performance = []
    for prop in properties:
        prop_reservations = reservations.filter(property_obj=prop)
        prop_revenue = prop_reservations.filter(payment_status='paid').aggregate(
            total=Sum('total_price')
        )['total'] or 0
        
        # Calculate occupancy for this property
        prop_rooms = getattr(prop, 'total_rooms', 1)
        occupied_rooms = prop_reservations.filter(
            status='confirmed',
            check_in__lte=timezone.now().date(),
            check_out__gte=timezone.now().date()
        ).count()
        prop_occupancy = (occupied_rooms / prop_rooms * 100) if prop_rooms > 0 else 0
        
        property_performance.append({
            'id': prop.id,
            'name': prop.name,
            'type': getattr(prop, 'type', 'Unknown'),
            'totalReservations': prop_reservations.count(),
            'revenue': prop_revenue,
            'occupancyRate': round(prop_occupancy, 1),
            'averageRating': getattr(prop, 'rating', 0)
        })
    
    # Cancellation analysis
    cancelled_reservations = reservations.filter(status='cancelled')
    cancellation_rate = (cancelled_reservations.count() / reservations.count() * 100) if reservations.count() > 0 else 0
    
    # Average length of stay
    completed_reservations = reservations.filter(status='completed')
    total_nights = sum(
        (r.check_out - r.check_in).days 
        for r in completed_reservations 
        if r.check_out and r.check_in
    )
    avg_length_of_stay = total_nights / completed_reservations.count() if completed_reservations.count() > 0 else 0
    
    # Seasonal trends (by quarter)
    seasonal_data = []
    current_year = timezone.now().year
    for quarter in range(1, 5):
        if quarter == 1:
            start_date = timezone.datetime(current_year, 1, 1).date()
            end_date = timezone.datetime(current_year, 3, 31).date()
        elif quarter == 2:
            start_date = timezone.datetime(current_year, 4, 1).date()
            end_date = timezone.datetime(current_year, 6, 30).date()
        elif quarter == 3:
            start_date = timezone.datetime(current_year, 7, 1).date()
            end_date = timezone.datetime(current_year, 9, 30).date()
        else:
            start_date = timezone.datetime(current_year, 10, 1).date()
            end_date = timezone.datetime(current_year, 12, 31).date()
        
        quarter_reservations = reservations.filter(
            check_in__gte=start_date,
            check_in__lte=end_date
        )
        
        seasonal_data.append({
            'quarter': f'Q{quarter}',
            'bookings': quarter_reservations.count(),
            'revenue': quarter_reservations.filter(payment_status='paid').aggregate(
                total=Sum('total_price')
            )['total'] or 0
        })
    
    performance_data = {
        'statusBreakdown': status_breakdown,
        'monthlyTrends': monthly_trends,
        'propertyPerformance': property_performance,
        'cancellationRate': round(cancellation_rate, 1),
        'averageLengthOfStay': round(avg_length_of_stay, 1),
        'seasonalTrends': seasonal_data,
        'totalReservations': reservations.count(),
        'confirmedReservations': reservations.filter(status='confirmed').count(),
        'cancelledReservations': cancelled_reservations.count(),
        'completedReservations': completed_reservations.count(),
        'totalRevenue': reservations.filter(payment_status='paid').aggregate(
            total=Sum('total_price')
        )['total'] or 0
    }
    
    return Response(performance_data)
