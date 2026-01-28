from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('property/<int:property_id>/', views.PropertyReviewListView.as_view(), name='property-reviews'),
    path('property/<int:property_id>/create/', views.create_review_view, name='create-review'),
    path('<int:review_id>/', views.ReviewDetailView.as_view(), name='review-detail'),
    path('<int:review_id>/update/', views.update_review_view, name='update-review'),
    path('<int:review_id>/respond/', views.respond_review_view, name='respond-review'),
    path('<int:review_id>/images/', views.upload_review_image_view, name='upload-review-image'),
    path('<int:review_id>/helpful/', views.mark_helpful_view, name='mark-helpful'),
    path('<int:review_id>/report/', views.report_review_view, name='report-review'),
    path('<int:review_id>/stats/', views.review_stats_view, name='review-stats'),
]
