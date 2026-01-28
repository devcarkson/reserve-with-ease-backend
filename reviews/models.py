from django.db import models
from django.contrib.auth import get_user_model
from properties.models import Property

User = get_user_model()


class Review(models.Model):
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    property_obj = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reviews')
    reservation = models.OneToOneField(
        'reservations.Reservation', 
        on_delete=models.CASCADE, 
        related_name='review',
        null=True,
        blank=True
    )
    rating = models.IntegerField(choices=RATING_CHOICES)
    title = models.CharField(max_length=255)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Owner response (legacy fields - keeping for backward compatibility)
    response_content = models.TextField(blank=True)
    response_created_at = models.DateTimeField(null=True, blank=True)
    responded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='review_responses'
    )

    # New owner response relationship
    owner_response = models.OneToOneField(
        'ReviewResponse',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parent_review'
    )
    
    # Detailed ratings
    cleanliness = models.IntegerField(null=True, blank=True)
    comfort = models.IntegerField(null=True, blank=True)
    location = models.IntegerField(null=True, blank=True)
    facilities = models.IntegerField(null=True, blank=True)
    staff = models.IntegerField(null=True, blank=True)
    value_for_money = models.IntegerField(null=True, blank=True)
    
    # Review status
    verified = models.BooleanField(default=False)
    helpful_count = models.IntegerField(default=0)
    reported = models.BooleanField(default=False)
    approved = models.BooleanField(default=False)  # Require admin approval
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['property_obj', 'user', 'reservation']
    
    def __str__(self):
        return f"Review by {self.user.username} for {self.property_obj.name}"
    
    @property
    def average_detailed_rating(self):
        ratings = [
            self.cleanliness, self.comfort, self.location,
            self.facilities, self.staff, self.value_for_money
        ]
        valid_ratings = [r for r in ratings if r is not None]
        return sum(valid_ratings) / len(valid_ratings) if valid_ratings else None


class ReviewImage(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='review_images/')
    caption = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Image for Review {self.review.id}"


class ReviewHelpful(models.Model):
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='helpful_votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['review', 'user']
    
    def __str__(self):
        return f"{self.user.username} found Review {self.review.id} helpful"


class ReviewReport(models.Model):
    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('inappropriate', 'Inappropriate Content'),
        ('fake', 'Fake Review'),
        ('offensive', 'Offensive Language'),
        ('irrelevant', 'Irrelevant'),
        ('other', 'Other'),
    ]
    
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='reports')
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    details = models.TextField(blank=True)
    resolved = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='resolved_reports'
    )
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['review', 'reporter']
    
    def __str__(self):
        return f"Report by {self.reporter.username} for Review {self.review.id}"


class PropertyReviewSummary(models.Model):
    property_obj = models.OneToOneField(Property, on_delete=models.CASCADE, related_name='review_summary')
    total_reviews = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0)
    
    # Detailed averages
    cleanliness_avg = models.FloatField(default=0)
    comfort_avg = models.FloatField(default=0)
    location_avg = models.FloatField(default=0)
    facilities_avg = models.FloatField(default=0)
    staff_avg = models.FloatField(default=0)
    value_for_money_avg = models.FloatField(default=0)
    
    # Rating distribution
    rating_1_count = models.IntegerField(default=0)
    rating_2_count = models.IntegerField(default=0)
    rating_3_count = models.IntegerField(default=0)
    rating_4_count = models.IntegerField(default=0)
    rating_5_count = models.IntegerField(default=0)
    rating_6_count = models.IntegerField(default=0)
    rating_7_count = models.IntegerField(default=0)
    rating_8_count = models.IntegerField(default=0)
    rating_9_count = models.IntegerField(default=0)
    rating_10_count = models.IntegerField(default=0)
    
    # Verified reviews
    verified_reviews = models.IntegerField(default=0)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Review Summary for {self.property_obj.name}"
    
    @property
    def rating_distribution(self):
        return {
            10: self.rating_10_count,
            9: self.rating_9_count,
            8: self.rating_8_count,
            7: self.rating_7_count,
            6: self.rating_6_count,
            5: self.rating_5_count,
            4: self.rating_4_count,
            3: self.rating_3_count,
            2: self.rating_2_count,
            1: self.rating_1_count,
        }
    
    @property
    def rating_percentages(self):
        total = self.total_reviews
        if total == 0:
            return {10: 0, 9: 0, 8: 0, 7: 0, 6: 0, 5: 0, 4: 0, 3: 0, 2: 0, 1: 0}

        return {
            10: (self.rating_10_count / total) * 100,
            9: (self.rating_9_count / total) * 100,
            8: (self.rating_8_count / total) * 100,
            7: (self.rating_7_count / total) * 100,
            6: (self.rating_6_count / total) * 100,
            5: (self.rating_5_count / total) * 100,
            4: (self.rating_4_count / total) * 100,
            3: (self.rating_3_count / total) * 100,
            2: (self.rating_2_count / total) * 100,
            1: (self.rating_1_count / total) * 100,
        }


class ReviewResponse(models.Model):
    review = models.OneToOneField(Review, on_delete=models.CASCADE, related_name='response_obj')
    responder = models.ForeignKey(User, on_delete=models.CASCADE, related_name='property_review_responses')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Response to Review {self.review.id} by {self.responder.username}"


class ReviewFlag(models.Model):
    FLAG_TYPE_CHOICES = [
        ('highlight', 'Highlight'),
        ('featured', 'Featured'),
        ('pinned', 'Pinned'),
        ('hidden', 'Hidden'),
    ]
    
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name='flags')
    flag_type = models.CharField(max_length=20, choices=FLAG_TYPE_CHOICES)
    flagged_by = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['review', 'flag_type']
    
    def __str__(self):
        return f"{self.flag_type} flag for Review {self.review.id}"


class ReviewAnalytics(models.Model):
    property_obj = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='review_analytics')
    date = models.DateField()
    reviews_count = models.IntegerField(default=0)
    average_rating = models.FloatField(default=0)
    response_rate = models.FloatField(default=0)
    response_time_hours = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['property_obj', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Analytics for {self.property_obj.name} on {self.date}"
