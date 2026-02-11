
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.http import HttpResponse
from django.core.mail import send_mail

# API Documentation Schema View
schema_view = get_schema_view(
    openapi.Info(
        title="Reserve With Ease API",
        default_version='v1',
        description="API for property reservation system",
        terms_of_service="https://www.google.com/policies/terms/",
        contact=openapi.Contact(email="contact@Carksontech@gmail.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=[permissions.AllowAny],
)


def test_email_view(request):
    """Test email endpoint - send a test email"""
    try:
        send_mail(
            'Test Email',
            'This is a test email from Reserve With Ease',
            'janetadmob@gmail.com',
            ['decarkson@gmail.com'],
            fail_silently=False,
        )
        return HttpResponse("Email sent successfully!")
    except Exception as e:
        return HttpResponse(f"Email failed: {str(e)}")


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include('accounts.urls')),
    
    # Test email endpoint
    path("api/test-email/", test_email_view, name='test_email'),
    
    path("api/properties/", include('properties.urls')),
    path("api/reservations/", include('reservations.urls')),
    path("api/reviews/", include('reviews.urls')),
    path("api/messaging/", include('messaging.urls')),
    path("api/payments/", include('payments.urls')),
    path("api/search/", include('search.urls')),
    path("api/dashboard/", include('dashboard.urls')),
    path("api/notifications/", include('notifications.urls')),
    
    # API Documentation
    re_path(r'^swagger(?P<format>\.json|\.yaml)$', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    re_path(r'^swagger/$', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    re_path(r'^redoc/$', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
