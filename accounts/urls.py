from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from . import views
from . import session_auth

app_name = 'accounts'

urlpatterns = [
    # Standard JWT token endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    
    # Session-based auth for Django admin users accessing frontend
    path('admin-session/', session_auth.admin_session_auth, name='admin_session_auth'),
    path('admin-login/', session_auth.admin_session_login, name='admin_session_login'),
    path('validate-admin-token/', session_auth.validate_admin_token, name='validate_admin_token'),
    
    # Custom registration and login
    path('register/', views.UserRegistrationView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('resend-verification/', views.resend_verification_email_view, name='resend_verification'),
    
    # Password reset URLs
    path('request-password-reset/', views.password_reset_request_view, name='request_password_reset'),
    path('reset-password/<str:token>/', views.reset_password_view, name='reset_password'),
    
    # Owner invitation URLs
    path('invitation/<str:token>/', views.invitation_verification_view, name='invitation_verification'),
    path('complete-invitation/<str:token>/', views.complete_owner_invitation_view, name='complete_invitation'),
    
    # Two-Factor Authentication URLs
    path('2fa/generate-secret/', views.generate_2fa_secret_view, name='generate_2fa_secret'),
    path('2fa/setup/', views.setup_2fa_view, name='setup_2fa'),
    path('2fa/verify/', views.verify_2fa_view, name='verify_2fa'),
    path('2fa/status/', views.get_2fa_status_view, name='get_2fa_status'),
    path('2fa/disable/', views.disable_2fa_view, name='disable_2fa'),
    path('2fa/regenerate-backup-codes/', views.regenerate_backup_codes_view, name='regenerate_backup_codes'),
    
    # Additional endpoints
    path('change-password/', views.change_password_view, name='change_password'),
    path('request-owner-invitation/', views.request_owner_invitation_view, name='request_owner_invitation'),
    
    # Wishlist URLs
    path('wishlist/', views.get_wishlist_view, name='wishlist'),
    path('wishlist/add/', views.add_to_wishlist_view, name='add_to_wishlist'),
    path('wishlist/remove/<int:property_id>/', views.remove_from_wishlist_view, name='remove_from_wishlist'),
    path('wishlist/check/<int:property_id>/', views.check_wishlist_view, name='check_wishlist'),
    path('wishlist/toggle/', views.toggle_wishlist_view, name='toggle_wishlist'),
]
