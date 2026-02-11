from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'notifications'

# API Router for ViewSets
router = DefaultRouter()
router.register(r'templates', views.EmailTemplateViewSet, basename='email-template')
router.register(r'notifications', views.EmailNotificationViewSet, basename='email-notification')

urlpatterns = [
    # API endpoints for ViewSets
    path('api/', include(router.urls)),
    
    # Email template generation API
    path('generate/', views.generate_email_template, name='generate-email-template'),
    
    # Custom email sending API
    path('send/', views.send_custom_email, name='send-custom-email'),
]
