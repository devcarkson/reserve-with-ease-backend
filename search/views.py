from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Avg
from properties.models import Property
from properties.serializers import PropertySerializer
from .models import SearchQuery, SearchClick, PopularSearch, SavedSearch, PropertySearchRanking
from .serializers import (
    SearchQuerySerializer, PopularSearchSerializer, SavedSearchSerializer,
    PropertySearchRankingSerializer, SearchSuggestionSerializer
)

User = get_user_model()


class SearchQueryListView(generics.ListAPIView):
    serializer_class = SearchQuerySerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    ordering = ['-created_at']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'admin':
            return SearchQuery.objects.all()
        else:
            return SearchQuery.objects.filter(user=user)


class PopularSearchListView(generics.ListAPIView):
    serializer_class = PopularSearchSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [filters.OrderingFilter]
    ordering = ['-search_count']

    def get_queryset(self):
        return PopularSearch.objects.all()


class SavedSearchListView(generics.ListCreateAPIView):
    serializer_class = SavedSearchSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return SavedSearch.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def search_suggestions_view(request):
    """Get search suggestions based on query"""
    query = request.query_params.get('q', '').strip()
    location = request.query_params.get('location', '').strip()
    
    if not query and not location:
        return Response({'suggestions': []})
    
    # Get popular searches
    popular_searches = PopularSearch.objects.all()
    suggestions = []
    
    if query:
        # Match by query
        query_matches = popular_searches.filter(
            query__icontains=query
        )[:5]
        suggestions.extend([
            {
                'query': item.query,
                'location': item.location,
                'type': 'query'
            }
            for item in query_matches
        ])
    
    if location:
        # Match by location
        location_matches = popular_searches.filter(
            location__icontains=location
        )[:5]
        suggestions.extend([
            {
                'query': item.query,
                'location': item.location,
                'type': 'location'
            }
            for item in location_matches
        ])
    
    # Add property suggestions
    if query or location:
        property_matches = Property.objects.filter(
            status='active'
        ).filter(
            Q(name__icontains=query) |
            Q(city__icontains=query) |
            Q(country__icontains=location)
        )[:5]
        
        suggestions.extend([
            {
                'query': prop.name,
                'location': f"{prop.city}, {prop.country}",
                'type': 'property',
                'property_id': prop.id
            }
            for prop in property_matches
        ])
    
    return Response({'suggestions': suggestions})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def trending_searches_view(request):
    """Get trending searches"""
    limit = int(request.query_params.get('limit', 10))
    
    trending = PopularSearch.objects.order_by('-search_count')[:limit]
    serializer = PopularSearchSerializer(trending, many=True)
    
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def location_trends_view(request):
    """Get location trends"""
    from datetime import timedelta
    from django.utils import timezone
    
    days = int(request.query_params.get('days', 30))
    start_date = timezone.now().date() - timedelta(days=days)
    
    trends = PropertySearchRanking.objects.filter(
        date__gte=start_date
    ).values('property__city').annotate(
        search_count=Count('property'),
        avg_price=Avg('total_price'),
        avg_rating=Avg('rating')
    ).order_by('-search_count')[:10]
    
    return Response({
        'trends': list(trends),
        'period_days': days
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def track_search_view(request):
    """Track search query and click"""
    # Track search query
    search_data = {
        'query': request.data.get('query', ''),
        'location': request.data.get('location', ''),
        'check_in': request.data.get('check_in'),
        'check_out': request.data.get('check_out'),
        'guests': request.data.get('guests'),
        'price_min': request.data.get('price_min'),
        'price_max': request.data.get('price_max'),
        'property_type': request.data.get('property_type'),
        'amenities': request.data.getlist('amenities', []),
        'filters': request.data.get('filters', {}),
    }
    
    serializer = SearchQuerySerializer(data=search_data)
    if serializer.is_valid():
        search_query = serializer.save()
        
        # Track property clicks if provided
        property_ids = request.data.getlist('property_ids', [])
        for i, property_id in enumerate(property_ids):
            try:
                property = Property.objects.get(id=property_id)
                SearchClick.objects.create(
                    search_query=search_query,
                    property=property,
                    position=i + 1
                )
            except Property.DoesNotExist:
                continue
        
        return Response({'tracked': True})
    
    return Response({'tracked': False, 'errors': serializer.errors})


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def save_search_view(request):
    """Save search for user"""
    search_data = {
        'query': request.data.get('query', ''),
        'location': request.data.get('location', ''),
        'check_in': request.data.get('check_in'),
        'check_out': request.data.get('check_out'),
        'guests': request.data.get('guests', 1),
        'price_min': request.data.get('price_min'),
        'price_max': request.data.get('price_max'),
        'property_type': request.data.get('property_type'),
        'amenities': request.data.getlist('amenities', []),
        'filters': request.data.get('filters', {}),
    }
    
    # Check if search already exists for this user
    existing_search = SavedSearch.objects.filter(
        user=request.user,
        query=search_data['query'],
        location=search_data['location']
    ).first()
    
    if existing_search:
        # Update existing search
        for key, value in search_data.items():
            if key in ['query', 'location', 'check_in', 'check_out', 'guests', 
                      'price_min', 'price_max', 'property_type', 'amenities']:
                setattr(existing_search, key, value)
        existing_search.save()
        return Response({'message': 'Search updated'})
    else:
        # Create new search
        serializer = SavedSearchSerializer(data=search_data)
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response({'message': 'Search saved'})
    
    return Response({'errors': serializer.errors})


class PropertySearchView(generics.ListAPIView):
    serializer_class = PropertySerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'city', 'country', 'description']
    ordering_fields = ['price_per_night', 'rating', 'created_at']
    ordering = ['-rating']

    def get_queryset(self):
        queryset = Property.objects.filter(status='active')
        
        # Get query parameters
        q = self.request.query_params.get('q', '')
        location = self.request.query_params.get('location', '')
        property_type = self.request.query_params.get('type', '')
        price_min = self.request.query_params.get('price_min', '')
        price_max = self.request.query_params.get('price_max', '')
        guests = self.request.query_params.get('guests', '')
        amenities = self.request.query_params.getlist('amenities', [])
        check_in = self.request.query_params.get('check_in', '')
        check_out = self.request.query_params.get('check_out', '')
        
        # Apply filters
        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) |
                Q(city__icontains=q) |
                Q(country__icontains=q) |
                Q(description__icontains=q)
            )
        
        if location:
            queryset = queryset.filter(
                Q(city__icontains=location) |
                Q(country__icontains=location)
            )
        
        if property_type:
            queryset = queryset.filter(type=property_type)
        
        # Filter by active discount
        is_discount_active = self.request.query_params.get('is_discount_active', '')
        if is_discount_active.lower() == 'true':
            from django.utils import timezone
            now = timezone.now()
            queryset = queryset.filter(
                has_discount=True,
                discount_end_date__gte=now
            )
        
        if price_min:
            queryset = queryset.filter(price_per_night__gte=price_min)
        
        if price_max:
            queryset = queryset.filter(price_per_night__lte=price_max)
        
        if guests:
            # Filter properties that have rooms with max_guests >= guests
            from properties.models import Room
            room_ids = Room.objects.filter(max_guests__gte=guests).values_list('property_id', flat=True)
            queryset = queryset.filter(id__in=room_ids)
        
        if amenities:
            # Filter properties that have all specified amenities
            for amenity in amenities:
                queryset = queryset.filter(amenities__icontains=amenity)
        
        # TODO: Add availability check based on reservations
        
        return queryset
