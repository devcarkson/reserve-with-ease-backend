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
@permission_classes([permissions.IsAuthenticated, IsOwnerUser])
def owner_dashboard_view(request):
    """Get dashboard stats for property owner"""
    user = request.user

    # Get or create owner dashboard stats
    stats, created = OwnerDashboardStats.objects.get_or_create(owner=user)

    # Update stats with real data
    properties = Property.objects.filter(owner=user)
    reservations = Reservation.objects.filter(property__owner=user)

    stats.total_properties = properties.count()
    stats.active_properties = properties.filter(status='active').count()
    stats.total_reservations = reservations.count()
    stats.upcoming_reservations = reservations.filter(
        status__in=['confirmed', 'pending'],
        check_in__gte=timezone.now().date()
    ).count()
    stats.current_reservations = reservations.filter(
        status='confirmed',
        check_in__lte=timezone.now().date(),
        check_out__gte=timezone.now().date()
    ).count()
    stats.completed_reservations = reservations.filter(status='completed').count()
    stats.cancelled_reservations = reservations.filter(status='cancelled').count()
    stats.total_revenue = reservations.filter(
        payment_status='paid'
    ).aggregate(total=Sum('total_price'))['total'] or 0

    # Monthly revenue (last 30 days)
    thirty_days_ago = timezone.now().date() - timedelta(days=30)
    stats.monthly_revenue = reservations.filter(
        payment_status='paid',
        created_at__date__gte=thirty_days_ago
    ).aggregate(total=Sum('total_price'))['total'] or 0

    # Average rating
    avg_rating = properties.aggregate(avg_rating=Avg('rating'))['avg_rating']
    stats.average_rating = avg_rating if avg_rating else 0

    # Total reviews
    stats.total_reviews = Review.objects.filter(property__owner=user).count()

    # Occupancy rate calculation (simplified)
    total_rooms = sum(prop.rooms.count() for prop in properties)
    if total_rooms > 0:
        occupied_rooms = reservations.filter(
            status='confirmed',
            check_in__lte=timezone.now().date(),
            check_out__gte=timezone.now().date()
        ).count()
        stats.occupancy_rate = (occupied_rooms / total_rooms) * 100
    else:
        stats.occupancy_rate = 0

    # Average daily rate
    if reservations.filter(payment_status='paid').exists():
        total_revenue = reservations.filter(payment_status='paid').aggregate(
            total=Sum('total_price')
        )['total'] or 0
        total_nights = sum((r.check_out - r.check_in).days for r in reservations.filter(payment_status='paid'))
        stats.average_daily_rate = total_revenue / total_nights if total_nights > 0 else 0
    else:
        stats.average_daily_rate = 0

    stats.save()

    serializer = OwnerDashboardStatsSerializer(stats)
    return Response(serializer.data)


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
