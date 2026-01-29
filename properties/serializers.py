from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Property, Room, PropertyImage, RoomImage, PropertyAvailability, RoomAvailability, PropertyFeature, PropertyReviewSummary, RoomCategory

User = get_user_model()


class PropertyImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyImage
        fields = '__all__'


class RoomImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomImage
        fields = '__all__'


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
        return {
            'id': obj.owner.id,
            'username': obj.owner.username,
            'get_full_name': obj.owner.get_full_name(),
            'profile_picture': obj.owner.profile_picture.url if obj.owner.profile_picture else None,
        }

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
        # Get minimum price from room categories or availability
        prices = []

        # Get prices from room categories
        room_category_prices = obj.room_categories.filter(base_price__gt=0).values_list('base_price', flat=True)
        prices.extend(room_category_prices)

        # Get prices from availability (calendar)
        availability_prices = obj.availability.filter(price__gt=0).values_list('price', flat=True)
        prices.extend(availability_prices)

        # Return minimum price if available, otherwise fallback to property price
        if prices:
            return min(prices)
        return obj.price_per_night

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
    class Meta:
        model = PropertyAvailability
        fields = '__all__'


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
    rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Property
        fields = ('id', 'name', 'type', 'city', 'country', 'rating', 'review_count',
                  'price_per_night', 'currency', 'main_image', 'featured', 'owner',
                  'location', 'images', 'amenities', 'description', 'free_cancellation', 'breakfast_included')

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
        # Return main image as array for compatibility
        if obj.main_image:
            return [obj.main_image]
        return []

    def get_amenities(self, obj):
        # Ensure amenities is a list
        return obj.amenities or []

    def get_price_per_night(self, obj):
        # Get minimum price from room categories or availability
        prices = []

        # Get prices from room categories
        room_category_prices = obj.room_categories.filter(base_price__gt=0).values_list('base_price', flat=True)
        prices.extend(room_category_prices)

        # Get prices from availability (calendar)
        availability_prices = obj.availability.filter(price__gt=0).values_list('price', flat=True)
        prices.extend(availability_prices)

        # Return minimum price if available, otherwise fallback to property price
        if prices:
            return min(prices)
        return obj.price_per_night


class RoomCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomCategory
        fields = '__all__'


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
