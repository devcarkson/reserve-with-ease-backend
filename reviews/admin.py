from django.contrib import admin
from .models import Review, ReviewImage, ReviewHelpful, ReviewReport, PropertyReviewSummary, ReviewResponse, ReviewFlag, ReviewAnalytics


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'property_obj', 'rating', 'approved', 'created_at')
    list_filter = ('approved', 'rating', 'created_at', 'property_obj')
    search_fields = ('user__username', 'user__email', 'property_obj__name', 'content')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['approve_reviews', 'reject_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(approved=True)
        self.message_user(request, f"{queryset.count()} review(s) approved.")
    approve_reviews.short_description = "Approve selected reviews"

    def reject_reviews(self, request, queryset):
        queryset.update(approved=False)
        self.message_user(request, f"{queryset.count()} review(s) rejected.")
    reject_reviews.short_description = "Reject selected reviews"


@admin.register(ReviewResponse)
class ReviewResponseAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'responder', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('review__user__username', 'responder__username', 'content')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(ReviewReport)
class ReviewReportAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'reporter', 'reason', 'resolved', 'created_at')
    list_filter = ('reason', 'resolved', 'created_at')
    search_fields = ('review__user__username', 'reporter__username', 'details')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['resolve_reports']

    def resolve_reports(self, request, queryset):
        queryset.update(resolved=True, resolved_by=request.user)
        self.message_user(request, f"{queryset.count()} report(s) resolved.")
    resolve_reports.short_description = "Resolve selected reports"


@admin.register(ReviewImage)
class ReviewImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'caption', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('review__user__username', 'caption')


@admin.register(ReviewHelpful)
class ReviewHelpfulAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('review__user__username', 'user__username')


@admin.register(PropertyReviewSummary)
class PropertyReviewSummaryAdmin(admin.ModelAdmin):
    list_display = ('id', 'property_obj', 'total_reviews', 'average_rating', 'updated_at')
    list_filter = ('updated_at',)
    search_fields = ('property_obj__name',)
    readonly_fields = ('updated_at',)


@admin.register(ReviewFlag)
class ReviewFlagAdmin(admin.ModelAdmin):
    list_display = ('id', 'review', 'flag_type', 'flagged_by', 'created_at')
    list_filter = ('flag_type', 'created_at')
    search_fields = ('review__user__username', 'flagged_by__username')


@admin.register(ReviewAnalytics)
class ReviewAnalyticsAdmin(admin.ModelAdmin):
    list_display = ('id', 'property_obj', 'date', 'reviews_count', 'average_rating')
    list_filter = ('date',)
    search_fields = ('property_obj__name',)
