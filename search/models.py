from django.db import models
from django.contrib.auth import get_user_model
from properties.models import Property

User = get_user_model()


class SearchQuery(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    query = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    guests = models.IntegerField(default=1)
    price_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    property_type = models.CharField(max_length=50, blank=True)
    amenities = models.JSONField(default=list)
    filters = models.JSONField(default=dict)
    results_count = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Search: {self.query} by {self.user.username if self.user else 'Anonymous'}"


class SearchClick(models.Model):
    search_query = models.ForeignKey(SearchQuery, on_delete=models.CASCADE, related_name='clicks')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='search_clicks')
    position = models.IntegerField()  # Position in search results
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Click on {self.property.name} from search {self.search_query.id}"


class PopularSearch(models.Model):
    query = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    search_count = models.IntegerField(default=0)
    click_through_rate = models.FloatField(default=0)
    avg_price_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avg_price_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    last_searched = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-search_count']
        unique_together = ['query', 'location']
    
    def __str__(self):
        return f"Popular: {self.query} in {self.location}"


class SavedSearch(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_searches')
    name = models.CharField(max_length=255)
    query = models.CharField(max_length=255)
    location = models.CharField(max_length=255, blank=True)
    check_in = models.DateField(null=True, blank=True)
    check_out = models.DateField(null=True, blank=True)
    guests = models.IntegerField(default=1)
    price_min = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    price_max = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    property_type = models.CharField(max_length=50, blank=True)
    amenities = models.JSONField(default=list)
    filters = models.JSONField(default=dict)
    email_notifications = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Saved search: {self.name} by {self.user.username}"


class SearchAnalytics(models.Model):
    date = models.DateField()
    total_searches = models.IntegerField(default=0)
    unique_searchers = models.IntegerField(default=0)
    avg_results_per_search = models.FloatField(default=0)
    click_through_rate = models.FloatField(default=0)
    top_locations = models.JSONField(default=list)
    top_queries = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Search analytics for {self.date}"


class PropertySearchRanking(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='search_rankings')
    date = models.DateField()
    search_impressions = models.IntegerField(default=0)
    search_clicks = models.IntegerField(default=0)
    search_bookings = models.IntegerField(default=0)
    avg_position = models.FloatField(default=0)
    relevance_score = models.FloatField(default=0)
    
    class Meta:
        unique_together = ['property', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Search ranking for {self.property.name} on {self.date}"


class SearchSuggestion(models.Model):
    query = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    popularity = models.IntegerField(default=0)
    property_count = models.IntegerField(default=0)
    avg_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-popularity']
        unique_together = ['query', 'location']
    
    def __str__(self):
        return f"Suggestion: {self.query} in {self.location}"


class SearchFilter(models.Model):
    FILTER_TYPE_CHOICES = [
        ('price_range', 'Price Range'),
        ('property_type', 'Property Type'),
        ('amenities', 'Amenities'),
        ('rating', 'Rating'),
        ('distance', 'Distance'),
        ('availability', 'Availability'),
    ]
    
    name = models.CharField(max_length=100)
    filter_type = models.CharField(max_length=20, choices=FILTER_TYPE_CHOICES)
    options = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['display_order', 'name']
    
    def __str__(self):
        return f"Filter: {self.name}"


class LocationTrend(models.Model):
    location = models.CharField(max_length=255)
    date = models.DateField()
    search_count = models.IntegerField(default=0)
    booking_count = models.IntegerField(default=0)
    avg_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    avg_rating = models.FloatField(default=0)
    property_count = models.IntegerField(default=0)
    
    class Meta:
        unique_together = ['location', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Trend for {self.location} on {self.date}"
