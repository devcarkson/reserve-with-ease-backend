from rest_framework import serializers
from django.contrib.auth import get_user_model
from properties.models import Property
from .models import Review, ReviewImage, ReviewHelpful, ReviewReport, PropertyReviewSummary, ReviewResponse

User = get_user_model()


class ReviewImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = '__all__'


class ReviewHelpfulSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewHelpful
        fields = '__all__'


class ReviewReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewReport
        fields = '__all__'


class PropertyReviewSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PropertyReviewSummary
        fields = '__all__'


class ReviewResponseSerializer(serializers.ModelSerializer):
    responder_name = serializers.CharField(source='responder.get_full_name', read_only=True)
    
    class Meta:
        model = ReviewResponse
        fields = '__all__'


class ReviewSerializer(serializers.ModelSerializer):
    property_name = serializers.CharField(source='property_obj.name', read_only=True)
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.profile_picture', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    response = ReviewResponseSerializer(source='response_obj', read_only=True)
    average_detailed_rating = serializers.ReadOnlyField()
    
    rating = serializers.SerializerMethodField()
    class Meta:
        model = Review
        fields = '__all__'
    
    def get_rating(self, obj):
        return obj.rating / 2 if obj.rating > 5 else obj.rating
        read_only_fields = ('user', 'property', 'created_at', 'updated_at')


class ReviewCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('rating', 'title', 'content', 'cleanliness', 'comfort', 
                  'location', 'facilities', 'staff', 'value_for_money')

    def validate(self, attrs):
        # Validate that detailed ratings are between 1-5 if provided
        detailed_fields = ['cleanliness', 'comfort', 'location', 'facilities', 'staff', 'value_for_money']
        for field in detailed_fields:
            if field in attrs and attrs[field] is not None:
                if not (1 <= attrs[field] <= 5):
                    raise serializers.ValidationError(f"{field} must be between 1 and 5")
        
        # Validate overall rating
        if 'rating' not in attrs or not (1 <= attrs['rating'] <= 10):
            raise serializers.ValidationError("Overall rating must be between 1 and 10")
        
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        property_id = self.context['property_id']

        # Allow multiple reviews - users can review properties multiple times
        # or update their existing reviews
        pass

        # Check if user has an existing unapproved review - if so, update it instead
        existing_unapproved_review = Review.objects.filter(
            user=user,
            property_obj_id=property_id,
            approved=False
        ).first()

        if existing_unapproved_review:
            # Update the existing unapproved review
            for attr, value in validated_data.items():
                setattr(existing_unapproved_review, attr, value)
            existing_unapproved_review.save()
            return existing_unapproved_review

        # Create new review
        validated_data['user'] = user
        validated_data['property_obj_id'] = property_id

        return super().create(validated_data)


class ReviewUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = ('rating', 'title', 'content', 'cleanliness', 'comfort', 
                  'location', 'facilities', 'staff', 'value_for_money')


class ReviewResponseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewResponse
        fields = ('content',)

    def create(self, validated_data):
        user = self.context['request'].user
        review = self.context['review']
        property_obj = review.property_obj

        # Check if user can respond to reviews based on owner type
        can_respond = False
        if user.owner_type == 'multi':
            # Multi-owners can respond to reviews for properties they own or created
            can_respond = (property_obj.owner == user or property_obj.created_by == user)
        elif user.owner_type == 'single':
            # Single owners can only respond to reviews for their own properties
            can_respond = (property_obj.owner == user)

        if not can_respond:
            raise serializers.ValidationError("Only property owners can respond to reviews")

        validated_data['responder'] = user
        validated_data['review'] = review

        return super().create(validated_data)


class PropertyReviewListSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    user_avatar = serializers.ImageField(source='user.profile_picture', read_only=True)
    images = ReviewImageSerializer(many=True, read_only=True)
    response = ReviewResponseSerializer(source='response_obj', read_only=True)
    
    class Meta:
        model = Review
        fields = ('id', 'rating', 'title', 'content', 'created_at', 
                  'user_name', 'user_avatar', 'images', 'response')


class ReviewStatsSerializer(serializers.Serializer):
    average_rating = serializers.FloatField()
    total_reviews = serializers.IntegerField()
    rating_distribution = serializers.DictField()
    detailed_ratings = serializers.DictField()


class ReviewWithHelpfulSerializer(ReviewSerializer):
    helpful_count = serializers.IntegerField(source='helpful_votes.count', read_only=True)
    user_has_marked_helpful = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = '__all__'
    
    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['rating'] = data['rating'] / 2
        return data

    def get_user_has_marked_helpful(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return ReviewHelpful.objects.filter(review=obj, user=request.user).exists()
        return False


class ReviewImageCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewImage
        fields = ('image', 'caption')

    def create(self, validated_data):
        review = self.context['review']
        validated_data['review'] = review
        return super().create(validated_data)


class ReviewReportCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewReport
        fields = ('reason', 'details')

    def create(self, validated_data):
        user = self.context['request'].user
        review = self.context['review']
        
        # Check if user has already reported this review
        if ReviewReport.objects.filter(review=review, reporter=user).exists():
            raise serializers.ValidationError("You have already reported this review")
        
        validated_data['reporter'] = user
        validated_data['review'] = review
        
        return super().create(validated_data)


class ReviewHelpfulCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewHelpful
        fields = ()

    def create(self, validated_data):
        user = self.context['request'].user
        review = self.context['review']
        
        # Check if user has already marked this review as helpful
        if ReviewHelpful.objects.filter(review=review, user=user).exists():
            raise serializers.ValidationError("You have already marked this review as helpful")
        
        # Check if user is reviewing their own review
        if review.user == user:
            raise serializers.ValidationError("You cannot mark your own review as helpful")
        
        validated_data['user'] = user
        validated_data['review'] = review
        
        return super().create(validated_data)
