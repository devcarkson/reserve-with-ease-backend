"""
Custom Admin Site with Messages Button
"""
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.template.response import TemplateResponse
from django.urls import path
from django.shortcuts import redirect
from django.utils.html import format_html
from django.utils.translation import gettext as _
from django.conf import settings


class ReserveWithEaseAdminSite(AdminSite):
    """Custom admin site with frontend link button"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('open-frontend-messages/', self.admin_view(self.open_frontend_messages), name='open_frontend_messages'),
        ]
        return custom_urls + urls
    
    def open_frontend_messages(self, request):
        """Redirect to frontend messages page - only for superusers"""
        if not request.user.is_superuser:
            from django.http import HttpResponseForbidden
            return HttpResponseForbidden("You must be a superuser to access this page.")
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')
        
        # Create a temporary token for frontend authentication
        import secrets
        from django.core.cache import cache
        token = secrets.token_urlsafe(32)
        cache.set(f'admin_session_token_{token}', request.user.id, timeout=300)  # 5 min expiry
        
        messages_url = f"{frontend_url}/admin/messages?admin_token={token}"
        return redirect(messages_url)
    
    def index(self, request, extra_context=None):
        """Override index to add frontend messages button"""
        extra_context = extra_context or {}
        extra_context['show_frontend_messages_button'] = True
        extra_context['frontend_messages_url'] = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/admin/messages"
        return super().index(request, extra_context)
    
    def each_context(self, request):
        """Add frontend messages button to every admin page"""
        context = super().each_context(request)
        context['show_frontend_messages_button'] = True
        context['frontend_messages_url'] = f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:8080')}/admin/messages"
        return context


# Create instance of custom admin site
admin_site = ReserveWithEaseAdminSite(name='admin')

# Register all existing models with the custom admin site
# Copy registrations from django.contrib.admin.site
from django.contrib.admin import site
from dashboard.models import (
    OwnerDashboardStats
)
from accounts.models import User, UserProfile
from properties.models import (
    PropertyType, Property, Room, PropertyImage, RoomImage,
    PropertyAvailability, RoomAvailability, PropertyFeature,
    PropertyReviewSummary, RoomCategory, Destination
)
from reservations.models import Reservation, Payment, Refund, Cancellation, CheckIn, CheckOut, BookingModification, ReviewInvitation
from reviews.models import Review, ReviewResponse, PropertyReviewSummary
from messaging.models import Conversation, Message
from notifications.models import Notification, EmailTemplate, EmailNotification
from payments.models import PaymentMethod, MonthlyInvoice

# Re-register all models with custom admin site
admin_site.register(User)
admin_site.register(UserProfile)
admin_site.register(PropertyType)
admin_site.register(Property)
admin_site.register(Room)
admin_site.register(PropertyImage)
admin_site.register(PropertyAvailability)
admin_site.register(PropertyReviewSummary)
admin_site.register(RoomCategory)
admin_site.register(Destination)
admin_site.register(Reservation)
admin_site.register(Refund)
admin_site.register(Cancellation)
admin_site.register(CheckIn)
admin_site.register(CheckOut)
admin_site.register(BookingModification)
admin_site.register(ReviewInvitation)
admin_site.register(Review)
admin_site.register(ReviewResponse)
admin_site.register(Conversation)
admin_site.register(Message)
admin_site.register(Notification)
admin_site.register(EmailNotification)
admin_site.register(OwnerDashboardStats)
admin_site.register(PaymentMethod)

# Register MonthlyInvoice with its admin class
from payments.admin import MonthlyInvoiceAdmin
admin_site.register(MonthlyInvoice, MonthlyInvoiceAdmin)
