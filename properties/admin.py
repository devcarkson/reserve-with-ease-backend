from django.contrib import admin
from .models import (
    PropertyType, Property, Room, PropertyImage, RoomImage, 
    PropertyAvailability, RoomAvailability, PropertyFeature, 
    PropertyReviewSummary
)


@admin.register(PropertyType)
class PropertyTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'image_url')
    search_fields = ('name', 'type')
    ordering = ('name',)
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'type')
        }),
        ('Image', {
            'fields': ('image',),
            'description': 'Upload an image to automatically save its R2 URL below.'
        }),
        ('R2 Image URL (Auto-generated)', {
            'fields': ('image_url',),
            'classes': ('collapse',),
            'description': 'This URL is automatically generated from the uploaded image.'
        }),
    )
    
    readonly_fields = ('image_url',)


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'city', 'country', 'owner', 'status', 'rating', 'formatted_price', 'featured', 'created_at')
    list_filter = ('type', 'status', 'featured', 'country', 'city', 'created_at')
    search_fields = ('name', 'city', 'country', 'address', 'owner__username', 'owner__email')
    ordering = ('-created_at',)
    readonly_fields = ('rating', 'review_count', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('name', 'type', 'city', 'country', 'address', 'owner', 'status')
        }),
        ('Location', {
            'fields': ('latitude', 'longitude', 'map_link'),
            'classes': ('collapse',)
        }),
        ('Pricing & Rating', {
            'fields': ('price_per_night', 'currency', 'rating', 'review_count'),
            'classes': ('collapse',)
        }),
        ('Features', {
            'fields': ('images', 'amenities', 'description', 'highlights', 'free_cancellation', 'breakfast_included'),
            'classes': ('collapse',)
        }),
        ('Policies', {
            'fields': ('check_in_time', 'check_out_time', 'express_check_in', 'cancellation_policy', 'house_rules'),
            'classes': ('collapse',)
        }),
        ('Additional Info', {
            'fields': ('featured', 'contacts', 'image_labels', 'main_image_index'),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def formatted_price(self, obj):
        return f"₦{obj.price_per_night:,.0f}"
    formatted_price.short_description = 'Price per Night'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Property owners can only see their own properties
        return qs.filter(owner=request.user)


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'property', 'type', 'max_guests', 'bed_type', 'size', 'formatted_price', 'available', 'created_at')
    list_filter = ('type', 'available', 'property', 'created_at')
    search_fields = ('name', 'property__name', 'type', 'bed_type')
    ordering = ('property', 'name')
    readonly_fields = ('created_at', 'updated_at')
    exclude = ('created_at', 'updated_at')

    def formatted_price(self, obj):
        return f"₦{obj.price_per_night:,.0f}"
    formatted_price.short_description = 'Price per Night'
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('property', 'name', 'type', 'max_guests', 'bed_type', 'size', 'available')
        }),
        ('Pricing', {
            'fields': ('price_per_night',),
            'classes': ('collapse',)
        }),
        ('Features', {
            'fields': ('amenities', 'images'),
            'classes': ('collapse',)
        }),
        ('System Fields', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        # Property owners can only see rooms for their properties
        return qs.filter(property__owner=request.user)


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property', 'label', 'is_main', 'order', 'created_at')
    list_filter = ('is_main', 'property', 'created_at')
    search_fields = ('property__name', 'label')
    ordering = ('property', 'order')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(property__owner=request.user)


@admin.register(RoomImage)
class RoomImageAdmin(admin.ModelAdmin):
    list_display = ('room', 'label', 'is_main', 'order', 'created_at')
    list_filter = ('is_main', 'room', 'created_at')
    search_fields = ('room__name', 'label')
    ordering = ('room', 'order')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(room__property__owner=request.user)


@admin.register(PropertyAvailability)
class PropertyAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('property', 'date', 'available', 'price', 'minimum_stay', 'created_at')
    list_filter = ('available', 'property', 'created_at')
    search_fields = ('property__name', 'date')
    ordering = ('property', '-date')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(property__owner=request.user)


@admin.register(RoomAvailability)
class RoomAvailabilityAdmin(admin.ModelAdmin):
    list_display = ('room', 'date', 'available', 'price', 'created_at')
    list_filter = ('available', 'room', 'created_at')
    search_fields = ('room__name', 'date')
    ordering = ('room', '-date')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(room__property__owner=request.user)


@admin.register(PropertyFeature)
class PropertyFeatureAdmin(admin.ModelAdmin):
    list_display = ('property', 'name', 'icon', 'created_at')
    list_filter = ('property', 'created_at')
    search_fields = ('property__name', 'name', 'description')
    ordering = ('property', 'name')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(property__owner=request.user)


@admin.register(PropertyReviewSummary)
class PropertyReviewSummaryAdmin(admin.ModelAdmin):
    list_display = ('property_obj', 'average_rating', 'total_reviews', 'cleanliness', 'comfort', 'location', 'facilities', 'staff', 'value_for_money', 'updated_at')
    list_filter = ('property_obj', 'updated_at')
    search_fields = ('property_obj__name',)
    ordering = ('-updated_at',)
    readonly_fields = ('average_rating', 'total_reviews', 'cleanliness', 'comfort', 'location', 'facilities', 'staff', 'value_for_money', 'updated_at')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(property_obj__owner=request.user)
