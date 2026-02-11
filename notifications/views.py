from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, AllowAny
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
import requests
import json
from django.conf import settings

from .models import EmailTemplate, EmailNotification
from .serializers import EmailTemplateSerializer, EmailNotificationSerializer


@api_view(['POST'])
@permission_classes([AllowAny])
def generate_email_template(request):
    """
    Generate email HTML using frontend templates
    This endpoint allows the backend to request email HTML from the frontend service
    """
    try:
        data = request.data
        template_type = data.get('type')
        template_data = data.get('data', {})
        
        if not template_type:
            return Response(
                {'error': 'Template type is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # In a real implementation, this would call the frontend service
        # For now, we'll return a basic template or forward the request
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        
        # This would be the frontend email generation service
        email_service_url = f"{frontend_url}/api/email/generate"
        
        try:
            # Try to call frontend service (if available)
            response = requests.post(
                email_service_url,
                json=data,
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return Response(response.json())
            else:
                # Fallback to basic template generation
                return generate_fallback_email(template_type, template_data)
                
        except requests.RequestException:
            # Frontend service not available, use fallback
            return generate_fallback_email(template_type, template_data)
            
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


def generate_fallback_email(template_type, data):
    """Generate a basic fallback email when frontend service is not available"""
    
    def get_subject():
        subjects = {
            'booking-confirmation': f"Booking Confirmed - {data.get('propertyName', 'Property')}",
            'owner-notification': f"New Booking - {data.get('propertyName', 'Property')}",
            'email-verification': 'Verify Your Email Address',
            'password-reset': 'Reset Your Password',
            'welcome': 'Welcome to Reserve With Ease',
            'review-response': f"Response to Your Review - {data.get('propertyName', 'Property')}"
        }
        return subjects.get(template_type, 'Reserve With Ease Notification')
    
    def get_html_content():
        if template_type == 'booking-confirmation':
            return f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #10b981;">Booking Confirmed!</h2>
                <p>Dear {data.get('guestFirstName', '')} {data.get('guestLastName', '')},</p>
                <p>Your booking at <strong>{data.get('propertyName', '')}</strong> has been confirmed.</p>
                <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>Property:</strong> {data.get('propertyName', '')}</p>
                    <p><strong>Check-in:</strong> {data.get('checkIn', '')}</p>
                    <p><strong>Check-out:</strong> {data.get('checkOut', '')}</p>
                    <p><strong>Total Price:</strong> ₦{data.get('totalPrice', '')}</p>
                </div>
                <p>Thank you for choosing Reserve With Ease!</p>
            </div>
            """
        elif template_type == 'owner-notification':
            return f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #f59e0b;">New Booking Received!</h2>
                <p>Hello {data.get('ownerName', '')},</p>
                <p>You have received a new booking for <strong>{data.get('propertyName', '')}</strong>.</p>
                <div style="background: #f9fafb; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p><strong>Guest:</strong> {data.get('guestFirstName', '')} {data.get('guestLastName', '')}</p>
                    <p><strong>Email:</strong> {data.get('guestEmail', '')}</p>
                    <p><strong>Check-in:</strong> {data.get('checkIn', '')}</p>
                    <p><strong>Check-out:</strong> {data.get('checkOut', '')}</p>
                    <p><strong>Total Price:</strong> ₦{data.get('totalPrice', '')}</p>
                </div>
                <p>Please respond to this booking within 24 hours.</p>
            </div>
            """
        elif template_type == 'email-verification':
            return f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #8b5cf6;">Verify Your Email Address</h2>
                <p>Welcome to Reserve With Ease!</p>
                <p>Please verify your email address by clicking the link below:</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{data.get('verificationUrl', '')}" 
                       style="background: #8b5cf6; color: white; padding: 15px 40px; text-decoration: none; border-radius: 6px;">
                        Verify Email Address
                    </a>
                </div>
                <p>This link will expire in 24 hours.</p>
            </div>
            """
        elif template_type == 'password-reset':
            return f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #ef4444;">Reset Your Password</h2>
                <p>We received a request to reset your password.</p>
                <div style="text-align: center; margin: 30px 0;">
                    <a href="{data.get('resetUrl', '')}" 
                       style="background: #ef4444; color: white; padding: 15px 40px; text-decoration: none; border-radius: 6px;">
                        Reset Password
                    </a>
                </div>
                <p>This link will expire in 1 hour for your security.</p>
            </div>
            """
        else:
            return f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2>Reserve With Ease Notification</h2>
                <p>This is a notification from Reserve With Ease.</p>
            </div>
            """
    
    def get_text_content():
        if template_type == 'booking-confirmation':
            return f"""
BOOKING CONFIRMED!

Dear {data.get('guestFirstName', '')} {data.get('guestLastName', '')},

Your booking at {data.get('propertyName', '')} has been confirmed.

Property: {data.get('propertyName', '')}
Check-in: {data.get('checkIn', '')}
Check-out: {data.get('checkOut', '')}
Total Price: ₦{data.get('totalPrice', '')}

Thank you for choosing Reserve With Ease!
            """
        elif template_type == 'owner-notification':
            return f"""
NEW BOOKING RECEIVED!

Hello {data.get('ownerName', '')},

You have received a new booking for {data.get('propertyName', '')}.

Guest: {data.get('guestFirstName', '')} {data.get('guestLastName', '')}
Email: {data.get('guestEmail', '')}
Check-in: {data.get('checkIn', '')}
Check-out: {data.get('checkOut', '')}
Total Price: ₦{data.get('totalPrice', '')}

Please respond within 24 hours.
            """
        else:
            return "Reserve With Ease Notification"
    
    return Response({
        'html': get_html_content(),
        'text': get_text_content(),
        'subject': get_subject()
    })


class EmailTemplateViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing email templates
    """
    queryset = EmailTemplate.objects.all()
    serializer_class = EmailTemplateSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = EmailTemplate.objects.all()
        template_type = self.request.query_params.get('type', None)
        if template_type:
            queryset = queryset.filter(template_type=template_type)
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        return queryset


class EmailNotificationViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing email notifications
    """
    queryset = EmailNotification.objects.all()
    serializer_class = EmailNotificationSerializer
    permission_classes = [IsAdminUser]
    
    def get_queryset(self):
        queryset = EmailNotification.objects.all()
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        recipient = self.request.query_params.get('recipient', None)
        if recipient:
            queryset = queryset.filter(recipient__icontains=recipient)
        return queryset


@api_view(['POST'])
@permission_classes([IsAdminUser])
def send_custom_email(request):
    """
    Send a custom email using the template system
    """
    try:
        data = request.data
        recipient = data.get('recipient')
        subject = data.get('subject')
        template_type = data.get('template_type')
        template_data = data.get('data', {})
        
        if not recipient or not subject:
            return Response(
                {'error': 'Recipient and subject are required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Generate email content
        from django.core.mail import send_mail
        from django.conf import settings
        
        # Try to get HTML from frontend template service
        try:
            template_response = requests.post(
                f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')}/api/email/generate",
                json={'type': template_type, 'data': template_data},
                timeout=10
            )
            
            if template_response.status_code == 200:
                email_data = template_response.json()
                html_content = email_data.get('html', '')
                text_content = email_data.get('text', '')
            else:
                # Use fallback
                fallback_response = generate_fallback_email(template_type, template_data)
                email_data = fallback_response.data
                html_content = email_data.get('html', '')
                text_content = email_data.get('text', '')
        except:
            # Use fallback
            fallback_response = generate_fallback_email(template_type, template_data)
            email_data = fallback_response.data
            html_content = email_data.get('html', '')
            text_content = email_data.get('text', '')
        
        # Create email notification record
        email_notification = EmailNotification.objects.create(
            recipient=recipient,
            subject=subject,
            html_content=html_content,
            text_content=text_content
        )
        
        # Send email
        send_mail(
            subject=subject,
            message=text_content,
            html_message=html_content,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@reservewithease.com'),
            recipient_list=[recipient],
            fail_silently=False,
        )
        
        email_notification.status = 'sent'
        email_notification.sent_at = timezone.now()
        email_notification.save()
        
        return Response({
            'message': 'Email sent successfully',
            'notification_id': email_notification.id
        })
        
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
