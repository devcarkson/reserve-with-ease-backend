from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('token/refresh/', views.token_refresh_view, name='token_refresh'),
    path('profile/', views.UserProfileView.as_view(), name='profile'),
    path('change-password/', views.change_password_view, name='change_password'),
    path('request-password-reset/', views.request_password_reset_view, name='request_password_reset'),
    path('reset-password/<str:token>/', views.reset_password_view, name='reset_password'),
    path('verify-email/<str:token>/', views.verify_email_view, name='verify_email'),
    path('request-owner-invitation/', views.request_owner_invitation_view, name='request_owner_invitation'),
    path('resend-verification/', views.resend_verification_email_view, name='resend_verification'),
]
