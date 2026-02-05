from rest_framework import generics, status, permissions, filters
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q, Avg, Count
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.files.storage import default_storage
from .utils import optimize_image_upload
from .models import PropertyType, Property, Room, PropertyImage, RoomImage, PropertyAvailability, RoomAvailability, PropertyFeature, PropertyReviewSummary, RoomCategory
from .serializers import (
    PropertyTypeSerializer, PropertySerializer, PropertyCreateSerializer, PropertyUpdateSerializer,
    PropertyListSerializer, RoomSerializer, RoomCreateSerializer, RoomUpdateSerializer,
    PropertyAvailabilitySerializer, RoomAvailabilitySerializer, PropertySearchSerializer,
    PropertyImageSerializer, RoomImageSerializer, RoomCategorySerializer, RoomCategoryCreateSerializer
)

# Import custom R2 storage
from reserve_at_ease.custom_storage import R2Storage

# Use R2 storage if enabled
from django.conf import settings
if settings.USE_R2:
    r2_storage = R2Storage()
else:
    r2_storage = default_storage

User = get_user_model()


class PropertyTypeListCreateView(generics.ListCreateAPIView):
    """
    List and create property types.
    - GET: Publicly accessible to all users (for property type carousel)
    - POST: Admin only (for managing property types)
    """
    queryset = PropertyType.objects.all()
    serializer_class = PropertyTypeSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        # Return all property types ordered by name
        return PropertyType.objects.all().order_by('name')


class PropertyTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a property type.
    Admin only for all operations.
    """
    queryset = PropertyType.objects.all()
    serializer_class = PropertyTypeSerializer
    permission_classes = [permissions.IsAdminUser]


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def property_types_public_view(request):
    """
    Public endpoint to get property types for home page carousel.
    This is cached for better performance.
    """
    try:
        property_types = PropertyType.objects.all().order_by('name')
        serializer = PropertyTypeSerializer(property_types, many=True)
        return Response(serializer.data)
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch property types: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


class IsOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.owner_type == 'multi':
            # Multi-owners can manage properties they own or created
            return obj.owner == user or obj.created_by == user
        elif user.owner_type == 'single':
            # Single owners can only manage their own properties
            return obj.owner == user
        else:
            # Users with no owner_type have no permissions
            return False


class PropertyListCreateView(generics.ListCreateAPIView):
    queryset = Property.objects.filter(status='active')
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'city', 'country', 'featured']
    search_fields = ['name', 'description', 'city', 'country', 'address']
    ordering_fields = ['price_per_night', 'rating', 'review_count', 'created_at']
    ordering = ['-rating']

    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return PropertyCreateSerializer
        return PropertyListSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = Property.objects.filter(status='active').filter(
            Q(price_per_night__gt=0) | Q(rooms__price_per_night__gt=0) | Q(room_categories__base_price__gt=0) | Q(availability__price__gt=0)
        ).distinct()
        
        # Custom filtering
        price_min = self.request.query_params.get('price_min')
        price_max = self.request.query_params.get('price_max')
        rating_min = self.request.query_params.get('rating_min')
        guests = self.request.query_params.get('guests')
        amenities = self.request.query_params.getlist('amenities')
        featured_only = self.request.query_params.get('featured_only')
        property_type_id = self.request.query_params.get('property_type_id')
        
        if price_min:
            queryset = queryset.filter(price_per_night__gte=price_min)
        if price_max:
            queryset = queryset.filter(price_per_night__lte=price_max)
        if rating_min:
            queryset = queryset.filter(rating__gte=rating_min)
        if guests:
            queryset = queryset.filter(rooms__max_guests__gte=guests).distinct()
        if amenities:
            for amenity in amenities:
                queryset = queryset.filter(amenities__contains=[amenity]).distinct()
        if featured_only == 'true':
            queryset = queryset.filter(featured=True)
        if property_type_id:
            # Get the PropertyType to get its type value
            try:
                property_type = PropertyType.objects.get(id=property_type_id)
                queryset = queryset.filter(type=property_type.type)
            except PropertyType.DoesNotExist:
                queryset = queryset.none()
        
        return queryset


class PropertyDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Property.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return PropertyUpdateSerializer
        return PropertySerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated(), IsOwner()]
        return [permissions.AllowAny()]


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def property_search_view(request):
    # Create cache key from query parameters
    cache_key = f"property_search_{hash(frozenset(request.query_params.items()))}"
    cached_result = cache.get(cache_key)

    if cached_result:
        return Response(cached_result)
    serializer = PropertySearchSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    
    queryset = Property.objects.filter(status='active')
    data = serializer.validated_data
    
    # Apply filters
    if data.get('query'):
        query = data['query']
        queryset = queryset.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(city__icontains=query) |
            Q(country__icontains=query) |
            Q(address__icontains=query)
        )
    
    if data.get('location'):
        location = data['location']
        queryset = queryset.filter(
            Q(city__icontains=location) |
            Q(country__icontains=location)
        )
    
    if data.get('price_min'):
        queryset = queryset.filter(price_per_night__gte=data['price_min'])
    
    if data.get('price_max'):
        queryset = queryset.filter(price_per_night__lte=data['price_max'])
    
    if data.get('rating_min'):
        queryset = queryset.filter(rating__gte=data['rating_min'])
    
    if data.get('property_type'):
        queryset = queryset.filter(type=data['property_type'])
    
    if data.get('amenities'):
        for amenity in data['amenities']:
            queryset = queryset.filter(amenities__contains=[amenity]).distinct()
    
    if data.get('guests'):
        queryset = queryset.filter(rooms__max_guests__gte=data['guests']).distinct()
    
    if data.get('featured_only'):
        queryset = queryset.filter(featured=True)
    
    # Apply sorting
    sort_by = data.get('sort_by', 'rating_high')
    if sort_by == 'price_low':
        queryset = queryset.order_by('price_per_night')
    elif sort_by == 'price_high':
        queryset = queryset.order_by('-price_per_night')
    elif sort_by == 'rating_high':
        queryset = queryset.order_by('-rating')
    elif sort_by == 'review_count':
        queryset = queryset.order_by('-review_count')
    
    # Serialize results
    serializer = PropertyListSerializer(queryset, many=True)
    result_data = {
        'count': queryset.count(),
        'results': serializer.data
    }

    # Cache the result for 5 minutes
    cache.set(cache_key, result_data, 300)

    return Response(result_data)


class RoomListCreateView(generics.ListCreateAPIView):
    serializer_class = RoomSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        property_id = self.kwargs['property_id']
        return Room.objects.filter(property_id=property_id)

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RoomCreateSerializer
        return RoomSerializer

    def perform_create(self, serializer):
        property_id = self.kwargs['property_id']
        property_obj = Property.objects.get(id=property_id)
        user = self.request.user

        # Check permissions based on owner type
        if user.owner_type == 'multi':
            # Multi-owners can manage properties they own or created
            if property_obj.owner != user and property_obj.created_by != user:
                raise permissions.PermissionDenied("You don't have permission to manage this property")
        elif user.owner_type == 'single':
            # Single owners can only manage their own properties
            if property_obj.owner != user:
                raise permissions.PermissionDenied("You don't have permission to manage this property")
        else:
            # Users with no owner_type have no permissions
            raise permissions.PermissionDenied("You don't have permission to manage properties")

        serializer.save(property=property_obj)


class RoomDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Room.objects.all()

    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return RoomUpdateSerializer
        return RoomSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated(), IsRoomOwner()]
        return [permissions.AllowAny()]


class IsRoomOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        user = request.user

        if user.owner_type == 'multi':
            # Multi-owners can manage rooms in properties they own or created
            return obj.property.owner == user or obj.property.created_by == user
        elif user.owner_type == 'single':
            # Single owners can only manage rooms in their properties
            return obj.property.owner == user
        else:
            # Users with no owner_type have no permissions
            return False


class RoomCategoryListCreateView(generics.ListCreateAPIView):
    serializer_class = RoomCategorySerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        property_id = self.kwargs['property_id']
        user = self.request.user

        # For GET requests (viewing), allow anyone to see room categories
        if self.request.method == 'GET':
            return RoomCategory.objects.filter(property_id=property_id)

        # For POST/PUT/DELETE (modifying), check permissions
        if user.owner_type == 'multi':
            # Multi-owners see room categories for properties they own or created
            return RoomCategory.objects.filter(
                property_id=property_id
            ).filter(
                Q(property__owner=user) | Q(property__created_by=user)
            )
        elif user.owner_type == 'single':
            # Single owners only see room categories for their properties
            return RoomCategory.objects.filter(
                property_id=property_id,
                property__owner=user
            )
        else:
            # Users with no owner_type see no room categories
            return RoomCategory.objects.none()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return RoomCategoryCreateSerializer
        return RoomCategorySerializer

    def perform_create(self, serializer):
        property_id = self.kwargs['property_id']
        property_obj = Property.objects.get(id=property_id)
        user = self.request.user

        # Check permissions based on owner type
        if user.owner_type == 'multi':
            # Multi-owners can manage properties they own or created
            if property_obj.owner != user and property_obj.created_by != user:
                raise permissions.PermissionDenied("You don't have permission to manage this property")
        elif user.owner_type == 'single':
            # Single owners can only manage their own properties
            if property_obj.owner != user:
                raise permissions.PermissionDenied("You don't have permission to manage this property")
        else:
            # Users with no owner_type have no permissions
            raise permissions.PermissionDenied("You don't have permission to manage properties")

        serializer.save(property=property_obj)


class RoomCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = RoomCategorySerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        user = self.request.user

        # For GET requests (viewing), allow anyone to see room categories
        if self.request.method == 'GET':
            return RoomCategory.objects.all()

        # For PUT/PATCH/DELETE (modifying), check permissions
        if user.owner_type == 'multi':
            # Multi-owners see room categories for properties they own or created
            return RoomCategory.objects.filter(
                Q(property__owner=user) | Q(property__created_by=user)
            )
        elif user.owner_type == 'single':
            # Single owners only see room categories for their properties
            return RoomCategory.objects.filter(property__owner=user)
        else:
            # Users with no owner_type see no room categories
            return RoomCategory.objects.none()


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_properties_view(request):
    user = request.user

    if user.owner_type == 'multi':
        # Multi-owners see properties they own OR created OR are authorized to manage
        properties = Property.objects.filter(
            Q(owner=user) | Q(created_by=user) | Q(authorized_users=user)
        ).distinct()
    elif user.owner_type == 'single':
        # Single owners see only their own properties
        properties = Property.objects.filter(owner=user)
    else:
        # Users with no owner_type see no properties
        properties = Property.objects.none()

    serializer = PropertySerializer(properties, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_property_image_view(request, property_id):
    try:
        property_obj = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if property_obj.owner != request.user:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    image = request.FILES.get('image')
    label = request.data.get('label', '')
    is_main = request.data.get('is_main', 'false').lower() == 'true'

    if not image:
        return Response({'error': 'Image file is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Optimize the uploaded image
    optimized_images = optimize_image_upload(image, 'property_image')

    # If this is marked as main, unmark other images
    if is_main:
        PropertyImage.objects.filter(property=property_obj).update(is_main=False)

    # Save the image using R2 storage
    image_file = optimized_images['compressed'] or optimized_images['original']
    image_path = r2_storage.save(f'property_images/{image_file.name}', image_file)
    
    property_image = PropertyImage.objects.create(
        property=property_obj,
        image=image_path,
        label=label,
        is_main=is_main
    )
    
    serializer = PropertyImageSerializer(property_image)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def upload_room_image_view(request, room_id):
    try:
        room = Room.objects.get(id=room_id)
    except Room.DoesNotExist:
        return Response({'error': 'Room not found'}, status=status.HTTP_404_NOT_FOUND)
    
    if room.property.owner != request.user:
        return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
    
    image = request.FILES.get('image')
    label = request.data.get('label', '')
    is_main = request.data.get('is_main', 'false').lower() == 'true'

    if not image:
        return Response({'error': 'Image file is required'}, status=status.HTTP_400_BAD_REQUEST)

    # Optimize the uploaded image
    optimized_images = optimize_image_upload(image, 'room_image')

    # If this is marked as main, unmark other images
    if is_main:
        RoomImage.objects.filter(room=room).update(is_main=False)

    # Save the image using R2 storage
    image_file = optimized_images['compressed'] or optimized_images['original']
    image_path = r2_storage.save(f'room_images/{image_file.name}', image_file)
    
    room_image = RoomImage.objects.create(
        room=room,
        image=image_path,
        label=label,
        is_main=is_main
    )
    
    serializer = RoomImageSerializer(room_image)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def property_availability_view(request, property_id):
    try:
        property_obj = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)

    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    if not start_date or not end_date:
        return Response({'error': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)

    availability = PropertyAvailability.objects.filter(
        property=property_obj,
        date__range=[start_date, end_date]
    ).order_by('date')

    serializer = PropertyAvailabilitySerializer(availability, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def property_calendar_view(request, property_id):
    """Get availability calendar for a property for a specific month"""
    try:
        property_obj = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)

    year = request.query_params.get('year')
    month = request.query_params.get('month')

    if not year or not month:
        return Response({'error': 'year and month are required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        year = int(year)
        month = int(month)
    except ValueError:
        return Response({'error': 'year and month must be integers'}, status=status.HTTP_400_BAD_REQUEST)

    # Get first and last day of the month
    from datetime import date
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)
    end_date = end_date.replace(day=1)  # This gives us the first day of next month

    # Get availability data for the month
    availability_records = PropertyAvailability.objects.filter(
        property=property_obj,
        date__gte=start_date,
        date__lt=end_date
    ).values('date', 'available', 'price')

    # Create a dictionary of date -> availability
    availability_dict = {}
    for record in availability_records:
        date_str = record['date'].isoformat()
        availability_dict[date_str] = {
            'available': record['available'],
            'price': record['price']
        }

    # If no availability records exist for this month, assume all dates are available
    # (This is the default behavior when no calendar data exists)
    if not availability_dict:
        current_date = start_date
        while current_date < end_date:
            date_str = current_date.isoformat()
            availability_dict[date_str] = {
                'available': True,
                'price': None
            }
            current_date = current_date.replace(day=current_date.day + 1)

    return Response({
        'property_id': property_id,
        'year': year,
        'month': month,
        'availability': availability_dict
    })


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def room_availability_view(request, room_id):
    try:
        room = Room.objects.get(id=room_id)
    except Room.DoesNotExist:
        return Response({'error': 'Room not found'}, status=status.HTTP_404_NOT_FOUND)
    
    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')
    
    if not start_date or not end_date:
        return Response({'error': 'start_date and end_date are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    availability = RoomAvailability.objects.filter(
        room=room,
        date__range=[start_date, end_date]
    ).order_by('date')
    
    serializer = RoomAvailabilitySerializer(availability, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def update_property_availability_view(request, property_id):
    """Update availability for a property for multiple dates"""
    try:
        property_obj = Property.objects.get(id=property_id)
    except Property.DoesNotExist:
        return Response({'error': 'Property not found'}, status=status.HTTP_404_NOT_FOUND)

    # Check if user has permission to update this property
    user = request.user
    has_permission = False

    if user.owner_type == 'multi':
        # Multi-owners can manage properties they own or created
        has_permission = property_obj.owner == user or property_obj.created_by == user
    elif user.owner_type == 'single':
        # Single owners can only manage their own properties
        has_permission = property_obj.owner == user
    else:
        # Users with no owner_type have no permissions
        has_permission = False

    if not has_permission:
        return Response({'error': 'You do not have permission to update this property'}, status=status.HTTP_403_FORBIDDEN)

    availability_data = request.data.get('availability', [])
    if not availability_data:
        return Response({'error': 'availability data is required'}, status=status.HTTP_400_BAD_REQUEST)

    updated_records = []
    for item in availability_data:
        date_str = item.get('date')
        available = item.get('available', True)
        price = item.get('price')

        if not date_str:
            continue

        # Update or create availability record
        availability, created = PropertyAvailability.objects.update_or_create(
            property=property_obj,
            date=date_str,
            defaults={
                'available': available,
                'price': price
            }
        )
        updated_records.append({
            'date': date_str,
            'available': available,
            'price': price,
            'created': created
        })

    return Response({
        'message': f'Updated {len(updated_records)} availability records',
        'updated': updated_records
    })
