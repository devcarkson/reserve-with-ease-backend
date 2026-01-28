from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.db.models import Q, Avg, Count
from properties.models import Property
from .models import Review, ReviewImage, ReviewHelpful, ReviewReport, PropertyReviewSummary, ReviewResponse
from .serializers import (
    ReviewSerializer, ReviewCreateSerializer, ReviewUpdateSerializer,
    PropertyReviewListSerializer, ReviewStatsSerializer, ReviewResponseCreateSerializer,
    ReviewResponseSerializer, ReviewImageCreateSerializer, ReviewReportCreateSerializer,
    ReviewHelpfulCreateSerializer, ReviewWithHelpfulSerializer
)

User = get_user_model()


class IsPropertyOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.property_obj.owner == request.user


class IsReviewOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.user == request.user


class CanEditReview(permissions.BasePermission):
    """Allow both review owner and property owner to edit reviews"""
    def has_object_permission(self, request, view, obj):
        # Allow if user is the review author
        if obj.user == request.user:
            return True
        # Allow if user is the property owner
        if obj.property_obj.owner == request.user:
            return True
        return False


class PropertyReviewListView(generics.ListAPIView):
    serializer_class = PropertyReviewListSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['rating']
    ordering_fields = ['created_at', 'rating']
    ordering = ['-created_at']

    def get_queryset(self):
        property_id = self.kwargs['property_id']
        return Review.objects.filter(property_obj_id=property_id, approved=True)


class ReviewDetailView(generics.RetrieveAPIView):
    queryset = Review.objects.all()
    serializer_class = ReviewWithHelpfulSerializer
    permission_classes = [permissions.AllowAny]


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def create_review_view(request, property_id):
    """Create a review for a property"""
    try:
        property_obj = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Temporarily disable reservation check for testing
    # Check if user has a completed reservation for this property
    # from reservations.models import Reservation
    # has_stayed = Reservation.objects.filter(
    #     user=request.user,
    #     property=property_obj,
    #     status='completed'
    # ).exists()
    #
    # if not has_stayed:
    #     return Response({'error': 'You must have completed a stay to review this property'},
    #                    status=status.HTTP_400_BAD_REQUEST)
    
    serializer = ReviewCreateSerializer(
        data=request.data,
        context={'request': request, 'property_id': property_id}
    )
    serializer.is_valid(raise_exception=True)
    review = serializer.save()
    
    # Update property rating
    update_property_rating(property_obj)
    
    return Response(
        ReviewSerializer(review).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated, IsReviewOwner])
def update_review_view(request, review_id):
    """Update a review (owner only)"""
    try:
        review = Review.objects.get(id=review_id, user=request.user)
    except Review.DoesNotExist:
        return Response({'error': 'Review not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = ReviewUpdateSerializer(review, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    updated_review = serializer.save()
    
    # Update property rating
    update_property_rating(updated_review.property_obj)
    
    return Response(ReviewSerializer(updated_review).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def respond_review_view(request, review_id):
    """Respond to a review (property owner only)"""
    try:
        review = Review.objects.get(id=review_id)
    except Review.DoesNotExist:
        return Response({'error': 'Review not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check if user can respond to reviews (owner or multi-owner of the property)
    user = request.user
    property_obj = review.property_obj

    can_respond = False
    if user.owner_type == 'multi':
        # Multi-owners can respond to reviews for properties they own or created
        can_respond = (property_obj.owner == user or property_obj.created_by == user)
    elif user.owner_type == 'single':
        # Single owners can only respond to reviews for their own properties
        can_respond = (property_obj.owner == user)
    # Users with no owner_type cannot respond

    if not can_respond:
        return Response({'error': 'Only property owners can respond to reviews'}, status=status.HTTP_403_FORBIDDEN)

    # Check if response already exists
    if hasattr(review, 'owner_response') and review.owner_response:
        return Response({'error': 'Response already exists'}, status=status.HTTP_400_BAD_REQUEST)

    serializer = ReviewResponseCreateSerializer(
        data=request.data,
        context={'request': request, 'review': review}
    )
    serializer.is_valid(raise_exception=True)
    response = serializer.save()

    # Send notification to reviewer
    from notifications.utils import send_review_response_notification
    send_review_response_notification(review)

    return Response(
        ReviewResponseSerializer(response).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_review_image_view(request, review_id):
    """Upload image for a review"""
    try:
        review = Review.objects.get(id=review_id, user=request.user)
    except Review.DoesNotExist:
        return Response({'error': 'Review not found'}, status=status.HTTP_404_NOT_FOUND)
    
    image = request.FILES.get('image')
    if not image:
        return Response({'error': 'Image file is required'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = ReviewImageCreateSerializer(
        data={'caption': request.data.get('caption', '')},
        context={'review': review}
    )
    serializer.is_valid(raise_exception=True)
    
    # Create image with file
    review_image = ReviewImage.objects.create(
        review=review,
        image=image,
        caption=serializer.validated_data['caption']
    )
    
    return Response(
        ReviewImageSerializer(review_image).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_helpful_view(request, review_id):
    """Mark a review as helpful"""
    try:
        review = Review.objects.get(id=review_id)
    except Review.DoesNotExist:
        return Response({'error': 'Review not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user already marked as helpful
    if ReviewHelpful.objects.filter(review=review, user=request.user).exists():
        return Response({'error': 'Already marked as helpful'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Check if user is reviewing their own review
    if review.user == request.user:
        return Response({'error': 'Cannot mark your own review as helpful'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = ReviewHelpfulCreateSerializer(
        data={},
        context={'request': request, 'review': review}
    )
    serializer.is_valid(raise_exception=True)
    helpful = serializer.save()
    
    # Update helpful count
    review.helpful_count = ReviewHelpful.objects.filter(review=review).count()
    review.save()
    
    return Response({'message': 'Marked as helpful'}, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def report_review_view(request, review_id):
    """Report a review"""
    try:
        review = Review.objects.get(id=review_id)
    except Review.DoesNotExist:
        return Response({'error': 'Review not found'}, status=status.HTTP_404_NOT_FOUND)
    
    # Check if user already reported this review
    if ReviewReport.objects.filter(review=review, reporter=request.user).exists():
        return Response({'error': 'Already reported this review'}, status=status.HTTP_400_BAD_REQUEST)
    
    serializer = ReviewReportCreateSerializer(
        data=request.data,
        context={'request': request, 'review': review}
    )
    serializer.is_valid(raise_exception=True)
    report = serializer.save()
    
    return Response(
        ReviewReportSerializer(report).data,
        status=status.HTTP_201_CREATED
    )


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def review_stats_view(request, review_id):
    """Get review statistics for a property"""
    try:
        review = Review.objects.get(id=review_id)
    except Review.DoesNotExist:
        return Response({'error': 'Review not found'}, status=status.HTTP_404_NOT_FOUND)
    
    property_obj = review.property_obj
    reviews = Review.objects.filter(property_obj=property_obj, approved=True)
    
    # Calculate statistics
    stats = {
        'total_reviews': reviews.count(),
        'average_rating': reviews.aggregate(avg_rating=Avg('rating'))['avg_rating'] or 0,
        'rating_distribution': {},
        'detailed_ratings': {
            'cleanliness': reviews.aggregate(avg=Avg('cleanliness'))['avg'] or 0,
            'comfort': reviews.aggregate(avg=Avg('comfort'))['avg'] or 0,
            'location': reviews.aggregate(avg=Avg('location'))['avg'] or 0,
            'facilities': reviews.aggregate(avg=Avg('facilities'))['avg'] or 0,
            'staff': reviews.aggregate(avg=Avg('staff'))['avg'] or 0,
            'value_for_money': reviews.aggregate(avg=Avg('value_for_money'))['avg'] or 0,
        }
    }
    
    # Rating distribution
    for rating in range(1, 11):
        stats['rating_distribution'][rating] = reviews.filter(rating=rating).count()
    
    return Response(stats)


def update_property_rating(property_obj):
    """Update property rating and review count"""
    reviews = Review.objects.filter(property_obj=property_obj, approved=True)
    
    if reviews.exists():
        avg_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
        property_obj.rating = round(avg_rating, 1) if avg_rating else 0
        property_obj.review_count = reviews.count()
    else:
        property_obj.rating = 0
        property_obj.review_count = 0
    
    property_obj.save()
    
    # Update or create review summary
    summary, created = PropertyReviewSummary.objects.get_or_create(property_obj=property_obj)
    
    # Update summary fields
    reviews_with_details = reviews.exclude(
        Q(cleanliness__isnull=True) &
        Q(comfort__isnull=True) &
        Q(location__isnull=True) &
        Q(facilities__isnull=True) &
        Q(staff__isnull=True) &
        Q(value_for_money__isnull=True)
    )
    
    if reviews_with_details.exists():
        summary.cleanliness_avg = reviews_with_details.aggregate(avg=Avg('cleanliness'))['avg'] or 0
        summary.comfort_avg = reviews_with_details.aggregate(avg=Avg('comfort'))['avg'] or 0
        summary.location_avg = reviews_with_details.aggregate(avg=Avg('location'))['avg'] or 0
        summary.facilities_avg = reviews_with_details.aggregate(avg=Avg('facilities'))['avg'] or 0
        summary.staff_avg = reviews_with_details.aggregate(avg=Avg('staff'))['avg'] or 0
        summary.value_for_money_avg = reviews_with_details.aggregate(avg=Avg('value_for_money'))['avg'] or 0
    
    summary.total_reviews = reviews.count()
    summary.average_rating = property_obj.rating
    summary.save()

