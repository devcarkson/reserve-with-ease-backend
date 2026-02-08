from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import PropertyType, Property, Room, PropertyImage, RoomImage, PropertyAvailability, RoomAvailability, PropertyFeature, PropertyReviewSummary, RoomCategory, Destination
from .utils import convert_image_urls_to_public

User = get_user_model()


class PropertyTypeSerializer(serializers.ModelSerializer):
    property_count = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyType
        fields = ['id', 'name', 'type', 'image_url', 'property_count']
    
    def get_property_count(self, obj):
        """Return count of active properties of this type"""
        from .models import Property
        return Property.objects.filter(type=obj.type, status='active').count()
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Make image_url the primary field, image is internal only
        return data


class PropertyImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyImage
        fields = ['id', 'property', 'image', 'image_url', 'label', 'is_main', 'order', 'created_at']
    
    def get_image_url(self, obj):
        if obj.image:
            # Convert to public R2 URL
            return convert_image_urls_to_public([obj.image.name])[0]
        return None


class RoomImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()
    
    class Meta:
        model = RoomImage
        fields = ['id', 'room', 'image', 'image_url', 'label', 'is_main', 'order', 'created_at']
    
    def get_image_url(self, obj):
        if obj.image:
            # Convert to public R2 URL
            return convert_image_urls_to_public([obj.image.name])[0]
        return None


class PropertyFeatureSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyFeature
        fields = '__all__'


class PropertyReviewSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyReviewSummary
        fields = '__all__'


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ['id', 'property', 'room_category', 'name', 'type', 'max_guests', 'bed_type', 'size', 'price_per_night', 'amenities', 'images', 'available', 'created_at', 'updated_at']
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Convert image URLs to public R2 format
        if 'images' in data and isinstance(data['images'], list):
            data['images'] = convert_image_urls_to_public(data['images'])
        return data


class PropertySerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    price_per_night = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = [
            'id', 'name', 'type', 'city', 'country', 'address', 'latitude', 'longitude',
            'rating', 'review_count', 'price_per_night', 'currency', 'images', 'amenities',
            'description', 'highlights', 'free_cancellation', 'breakfast_included', 'featured',
            'owner', 'status', 'map_link', 'check_in_time', 'check_out_time', 'express_check_in',
            'cancellation_policy', 'house_rules', 'contacts', 'image_labels', 'main_image_index',
            'created_at', 'updated_at', 'location'
        ]

    rating = serializers.SerializerMethodField()

    def get_owner(self, obj):
        if not obj.owner:
            return {'id': None, 'username': 'Unknown', 'get_full_name': '', 'profile_picture': None}
        try:
            return {
                'id': obj.owner.id,
                'username': obj.owner.username,
                'get_full_name': obj.owner.get_full_name(),
                'profile_picture': obj.owner.profile_picture.url if obj.owner.profile_picture else None,
            }
        except Exception:
            return {'id': obj.owner.id if hasattr(obj.owner, 'id') else None, 'username': 'Unknown', 'get_full_name': '', 'profile_picture': None}

    def get_rating(self, obj):
        reviews = obj.reviews.all()
        if reviews.exists():
            total = sum(review.rating for review in reviews)
            return round(total / reviews.count(), 1)
        return obj.rating

    review_count = serializers.SerializerMethodField()

    def get_review_count(self, obj):
        return obj.reviews.count()

    def get_location(self, obj):
        return {
            'city': obj.city or '',
            'country': obj.country or '',
            'address': obj.address or '',
            'coordinates': {
                'lat': obj.latitude or 0,
                'lng': obj.longitude or 0
            }
        }

    def get_price_per_night(self, obj):
        # Get minimum effective price from room categories or availability
        prices = []

        # Get effective prices from room categories (includes discounts)
        try:
            for room_category in obj.room_categories.all():
                base_price = room_category.base_price if room_category else 0
                effective_price = room_category.get_effective_price(base_price)
                if effective_price and effective_price > 0:
                    prices.append(effective_price)
        except Exception:
            pass

        # Get effective prices from availability (includes discounts)
        try:
            for availability in obj.availability.all():
                base_price = availability.price if availability else 0
                effective_price = availability.get_effective_price(base_price)
                if effective_price and effective_price > 0:
                    prices.append(effective_price)
        except Exception:
            pass

        # Return minimum effective price if available, otherwise fallback to property price
        if prices:
            return min(prices)
        return obj.price_per_night if obj.price_per_night else 0


    def get_has_discount(self, obj):
        """Check if property has any active discounts"""
        from django.utils import timezone
        today = timezone.now().date()
        
        # Check room categories for active discounts
        has_category_discount = obj.room_categories.filter(
            has_discount=True,
            discount_start_date__lte=today,
            discount_end_date__gte=today
        ).exists()
        
        # Check availability for active discounts
        has_availability_discount = obj.availability.filter(
            has_discount=True
        ).exists()
        
        return has_category_discount or has_availability_discount

    def get_discount_percentage(self, obj):
        """Get highest discount percentage from room categories"""
        from django.utils import timezone
        today = timezone.now().date()
        
        discount_categories = obj.room_categories.filter(
            has_discount=True,
            discount_start_date__lte=today,
            discount_end_date__gte=today
        ).order_by('-discount_percentage').first()
        
        if discount_categories:
            return discount_categories.discount_percentage
        return 0

    def get_is_discount_active(self, obj):
        """Check if any discount is currently active"""
        return self.get_has_discount(obj)

    def get_owner(self, obj):
        return {
            'id': obj.owner.id,
            'username': obj.owner.username,
            'get_full_name': obj.owner.get_full_name(),
            'profile_picture': obj.owner.profile_picture.url if obj.owner.profile_picture else None,
        }

    def get_formatted_price(self, obj):
        price = self.get_price_per_night(obj)
        if price is None:
            return "₦0"
        return f"₦{price:,.0f}"

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Ensure JSONField data is properly serialized
        json_fields = ['images', 'amenities', 'highlights', 'cancellation_policy', 'house_rules', 'contacts', 'image_labels']
        for field in json_fields:
            if field in data:
                try:
                    # Ensure it's a list/dict, default to empty list if None or invalid
                    if data[field] is None or not isinstance(data[field], (list, dict)):
                        data[field] = []
                except:
                    data[field] = []
        
        # Convert image URLs to public R2 format
        if 'images' in data and isinstance(data['images'], list):
            data['images'] = convert_image_urls_to_public(data['images'])
        
        return data


class PropertyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        exclude = ('owner',)

    def create(self, validated_data):
        validated_data['owner'] = self.context['request'].user
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class PropertyUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Property
        exclude = ('created_at', 'updated_at')


class RoomCreateSerializer(serializers.ModelSerializer):
    room_category = serializers.PrimaryKeyRelatedField(queryset=RoomCategory.objects.all(), required=False)

    class Meta:
        model = Room
        fields = '__all__'

    def create(self, validated_data):
        room_category = validated_data.pop('room_category', None)
        if room_category:
            validated_data['name'] = room_category.name
            validated_data['max_guests'] = room_category.max_occupancy
            validated_data['bed_type'] = room_category.bed_type
            validated_data['size'] = room_category.size
            validated_data['price_per_night'] = room_category.base_price
            validated_data['amenities'] = room_category.amenities
        return super().create(validated_data)


class RoomUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        exclude = ('property', 'created_at', 'updated_at')


class PropertyAvailabilitySerializer(serializers.ModelSerializer):
    effective_price = serializers.SerializerMethodField()
    
    class Meta:
        model = PropertyAvailability
        fields = '__all__'
    
    def get_effective_price(self, obj):
        # Get base price from property's room categories
        room_category = obj.property.room_categories.first()
        base_price = room_category.base_price if room_category else 0
        return obj.get_effective_price(base_price)


class RoomAvailabilitySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomAvailability
        fields = '__all__'


class PropertyListSerializer(serializers.ModelSerializer):
    owner = serializers.SerializerMethodField()
    main_image = serializers.ReadOnlyField()
    location = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()
    amenities = serializers.SerializerMethodField()
    price_per_night = serializers.SerializerMethodField()
    original_price = serializers.SerializerMethodField()
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()
    has_discount = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    is_discount_active = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = ('id', 'name', 'type', 'city', 'country', 'rating', 'review_count',
                  'price_per_night', 'original_price', 'currency', 'main_image', 'featured', 'owner',
                  'location', 'images', 'amenities', 'description', 'free_cancellation', 
                  'breakfast_included', 'has_discount', 'discount_percentage', 'is_discount_active')

    def get_owner(self, obj):
        return {
            'id': obj.owner.id,
            'username': obj.owner.username,
            'get_full_name': obj.owner.get_full_name(),
            'profile_picture': obj.owner.profile_picture.url if obj.owner.profile_picture else None,
        }

    def get_rating(self, obj):
        return obj.rating

    def get_review_count(self, obj):
        return obj.review_count

    def get_location(self, obj):
        return {
            'city': obj.city or '',
            'country': obj.country or '',
            'address': obj.address or '',
            'coordinates': {
                'lat': obj.latitude or 0,
                'lng': obj.longitude or 0
            }
        }

    def get_images(self, obj):
        # Return main image as array for compatibility with conversion
        if obj.main_image:
            converted = convert_image_urls_to_public([obj.main_image])
            return converted
        return []

    def get_amenities(self, obj):
        # Ensure amenities is a list
        return obj.amenities or []

    def get_price_per_night(self, obj):
        # Get minimum effective price from room categories or availability
        prices = []

        # Get effective prices from room categories (includes discounts)
        for room_category in obj.room_categories.all():
            if room_category.base_price and room_category.base_price > 0:
                effective_price = room_category.get_effective_price()
                if effective_price and effective_price > 0:
                    prices.append(effective_price)

        # Get effective prices from availability (includes discounts)
        for availability in obj.availability.all():
            if availability.price and availability.price > 0:
                room_category = obj.room_categories.first()
                base_price = room_category.base_price if room_category and room_category.base_price else 0
                effective_price = availability.get_effective_price(base_price)
                if effective_price and effective_price > 0:
                    prices.append(effective_price)

        # Return minimum effective price if available, otherwise fallback to property price
        if prices:
            return min(prices)
        # Fallback to property's price_per_night (ensure it's not 0)
        if obj.price_per_night and float(obj.price_per_night) > 0:
            return float(obj.price_per_night)
        return 0

    def get_original_price(self, obj):
        """Get original/base price (before discount) from room categories"""
        # Get minimum base price from room categories
        base_prices = []
        for room_category in obj.room_categories.all():
            if room_category.base_price and room_category.base_price > 0:
                base_prices.append(float(room_category.base_price))
        
        if base_prices:
            return min(base_prices)
        # Fallback to property's price_per_night (ensure it's not 0)
        if obj.price_per_night and float(obj.price_per_night) > 0:
            return float(obj.price_per_night)
        return 0

    def get_has_discount(self, obj):
        """Check if property has any active discounts"""
        from django.utils import timezone
        today = timezone.now().date()
        
        # Check room categories for active discounts
        has_category_discount = obj.room_categories.filter(
            has_discount=True,
            discount_start_date__lte=today,
            discount_end_date__gte=today
        ).exists()
        
        # Check availability for active discounts
        has_availability_discount = obj.availability.filter(
            has_discount=True
        ).exists()
        
        return has_category_discount or has_availability_discount

    def get_discount_percentage(self, obj):
        """Get highest discount percentage from room categories"""
        from django.utils import timezone
        today = timezone.now().date()
        
        discount_categories = obj.room_categories.filter(
            has_discount=True,
            discount_start_date__lte=today,
            discount_end_date__gte=today
        ).order_by('-discount_percentage').first()
        
        if discount_categories:
            return discount_categories.discount_percentage
        return 0

    def get_is_discount_active(self, obj):
        """Check if any discount is currently active"""
        return self.get_has_discount(obj)


class RoomCategorySerializer(serializers.ModelSerializer):
    effective_price = serializers.SerializerMethodField()
    is_discount_active = serializers.SerializerMethodField()
    
    class Meta:
        model = RoomCategory
        fields = '__all__'
    
    def get_effective_price(self, obj):
        """Get current price with discount if active"""
        return obj.get_effective_price()
    
    def get_is_discount_active(self, obj):
        """Check if discount is currently active based on dates"""
        return obj.is_discount_active()


class RoomCategoryCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomCategory
        exclude = ('property',)


class PropertySearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=False, allow_blank=True)
    location = serializers.CharField(required=False, allow_blank=True)
    check_in = serializers.DateField(required=False)
    check_out = serializers.DateField(required=False)
    guests = serializers.IntegerField(required=False, min_value=1, default=1)
    price_min = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    price_max = serializers.DecimalField(required=False, max_digits=10, decimal_places=2)
    property_type = serializers.CharField(required=False, allow_blank=True)
    amenities = serializers.ListField(required=False, child=serializers.CharField())
    rating_min = serializers.IntegerField(required=False, min_value=1, max_value=5)
    featured_only = serializers.BooleanField(required=False, default=False)
    sort_by = serializers.ChoiceField(
        required=False,
        choices=['price_low', 'price_high', 'rating_high', 'review_count'],
        default='rating_high'
    )


class DestinationSerializer(serializers.ModelSerializer):
    """Serializer for Destination model"""
    image_url = serializers.SerializerMethodField()
    property_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Destination
        fields = ['id', 'name', 'image_url', 'sort_order', 'property_count']
    
    def get_image_url(self, obj):
        """Return the image URL (either from image_url field or from uploaded image)"""
        if obj.image_url:
            return obj.image_url
        if obj.image:
            # Convert to public R2 URL format using the utility function
            return convert_image_urls_to_public([obj.image.name])[0]
        return None
    
    def get_property_count(self, obj):
        """Return count of active properties in this destination/city"""
        from .models import Property
        return Property.objects.filter(city__iexact=obj.name, status='active').count()


class DestinationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating Destination"""
    image_url = serializers.URLField(required=False, allow_blank=True, allow_null=True)
    
    class Meta:
        model = Destination
        fields = ['id', 'name', 'image', 'image_url', 'sort_order']
    
    def validate(self, attrs):
        """
        Validate that either image or image_url is provided, but not both required.
        """
        image = attrs.get('image')
        image_url = attrs.get('image_url')
        
        # If no image and no image_url, that's fine (destination can exist without images)
        # If image is provided, image_url can be empty (will be auto-populated)
        # If image_url is provided, image can be empty (external URL)
        
        return attrs
