from django.db import models
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

# Import R2 storage if enabled
if settings.USE_R2:
    from reserve_at_ease.custom_storage import R2Storage
    r2_storage = R2Storage()
else:
    from django.core.files.storage import default_storage
    r2_storage = default_storage


class PropertyType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=50, unique=True)  # URL-friendly type identifier
    image = models.ImageField(upload_to='property_types/', storage=r2_storage, blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)  # URL for images (R2 or external)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Property Types'

    def __str__(self):
        return self.name


class Property(models.Model):
    TYPE_CHOICES = [
        ('hotel', 'Hotel'),
        ('apartment', 'Apartment'),
        ('villa', 'Villa'),
        ('resort', 'Resort'),
        ('hostel', 'Hostel'),
    ]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('pending', 'Pending'),
        ('inactive', 'Inactive'),
    ]
    
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    city = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    address = models.TextField()
    latitude = models.FloatField()
    longitude = models.FloatField()
    rating = models.FloatField(default=0)
    review_count = models.IntegerField(default=0)
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='NGN')
    images = models.JSONField(default=list)  # List of URLs
    amenities = models.JSONField(default=list)  # List of strings
    description = models.TextField()
    highlights = models.JSONField(default=list)  # List of strings
    free_cancellation = models.BooleanField(default=False)
    breakfast_included = models.BooleanField(default=False)
    featured = models.BooleanField(default=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='properties')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_properties')
    authorized_users = models.ManyToManyField(User, related_name='authorized_properties', blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    map_link = models.URLField(max_length=50000, blank=True)
    check_in_time = models.CharField(max_length=10, default='14:00')
    check_out_time = models.CharField(max_length=10, default='11:00')
    express_check_in = models.BooleanField(default=False)
    cancellation_policy = models.JSONField(default=list)  # List of strings
    house_rules = models.JSONField(default=list)  # List of strings
    contacts = models.JSONField(default=list, blank=True)  # List of contact dicts
    image_labels = models.JSONField(default=list, blank=True)  # List of labels for images
    main_image_index = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.city}"
    
    @property
    def main_image(self):
        if self.images and len(self.images) > self.main_image_index:
            return self.images[self.main_image_index]
        return self.images[0] if self.images else None


class Room(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='rooms')
    room_category = models.ForeignKey('RoomCategory', on_delete=models.CASCADE, related_name='rooms', null=True, blank=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)
    max_guests = models.IntegerField()
    bed_type = models.CharField(max_length=50)
    size = models.IntegerField()  # sqm
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)
    amenities = models.JSONField(default=list)
    images = models.JSONField(default=list)
    available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['price_per_night']
    
    def __str__(self):
        return f"{self.name}"


class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='property_images')
    image = models.ImageField(upload_to='property_images/')
    label = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Image for {self.property.name}"


class RoomImage(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='room_images')
    image = models.ImageField(upload_to='room_images/')
    label = models.CharField(max_length=255, blank=True)
    is_main = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"Image for {self.room.name}"


class PropertyAvailability(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='availability')
    date = models.DateField()
    available = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    minimum_stay = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['property', 'date']
        ordering = ['date']
    
    def __str__(self):
        return f"{self.property.name} - {self.date}"


class RoomAvailability(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name='availability')
    date = models.DateField()
    available = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['room', 'date']
        ordering = ['date']

    def __str__(self):
        return f"{self.room.name} - {self.date}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)


class PropertyFeature(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='features')
    name = models.CharField(max_length=100)
    icon = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['property', 'name']
    
    def __str__(self):
        return f"{self.property.name} - {self.name}"


class RoomCategory(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='room_categories')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    max_occupancy = models.IntegerField()
    bed_type = models.CharField(max_length=50, blank=True)
    size = models.IntegerField(default=0)  # sqm
    amenities = models.JSONField(default=list)  # List of amenity IDs
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} - {self.property.name}"

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        # Update all rooms in this category to match category properties
        existing_rooms = list(self.rooms.all())
        for room in existing_rooms:
            room.name = self.name
            room.max_guests = self.max_occupancy
            room.bed_type = self.bed_type
            room.size = self.size
            room.price_per_night = self.base_price
            room.amenities = self.amenities
            room.save()

        # If this is a new category or no rooms exist, create a default room
        if is_new or not existing_rooms:
            if not existing_rooms:
                Room.objects.create(
                    property=self.property,
                    room_category=self,
                    name=self.name,
                    type=self.name,  # Use category name as type
                    max_guests=self.max_occupancy,
                    bed_type=self.bed_type,
                    size=self.size,
                    price_per_night=self.base_price,
                    amenities=self.amenities,
                    available=True
                )


class PropertyReviewSummary(models.Model):
    property_obj = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='property_review_summary')
    cleanliness = models.FloatField(default=0)
    comfort = models.FloatField(default=0)
    location = models.FloatField(default=0)
    facilities = models.FloatField(default=0)
    staff = models.FloatField(default=0)
    value_for_money = models.FloatField(default=0)
    total_reviews = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review Summary for {self.property_obj.name}"
