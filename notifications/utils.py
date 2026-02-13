from django.template.loader import render_to_string
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.utils import timezone
import requests
import json
from .models import EmailTemplate, EmailNotification, Notification


def send_html_email(subject, html_content, recipient_list, text_content=None):
    """Send HTML email with optional plain text fallback"""
    try:
        sender_name = getattr(settings, 'EMAIL_SENDER_NAME', 'Reservewithease')
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', f'{sender_name} <noreply@reservewithease.com>')
        
        print(f"DEBUG: Attempting to send email to {recipient_list}")
        print(f"DEBUG: From: {from_email}")
        print(f"DEBUG: Subject: {subject}")
        print(f"DEBUG: Email backend: {getattr(settings, 'EMAIL_BACKEND', 'default')}")
        
        if text_content:
            # Send HTML with plain text alternative
            msg = EmailMultiAlternatives(subject, text_content, from_email, recipient_list)
            msg.attach_alternative(html_content, "text/html")
            result = msg.send(fail_silently=False)
        else:
            # Send HTML only
            result = send_mail(
                subject,
                '',
                from_email,
                recipient_list,
                fail_silently=False,
                html_message=html_content
            )
        
        if result:
            print(f"SUCCESS: Email sent successfully to {recipient_list}")
            return True
        else:
            print(f"FAILED: Email send returned False for {recipient_list}")
            return False
            
    except Exception as e:
        print(f"ERROR: Exception sending email: {e}")
        print(f"ERROR: Exception type: {type(e)}")
        import traceback
        traceback.print_exc()
        return False


def render_email_template(template_name, context):
    """Render an email template with context"""
    # Template path: notifications/templates/{template_name}.html
    template_path = f"{template_name}.html"
    
    try:
        html_content = render_to_string(template_path, context)
        return html_content
    except Exception as e:
        print(f"Error rendering template {template_path}: {e}")
        return None


def send_email_verification_email(user, verification_url):
    """Send email verification email using template"""
    context = {
        'verification_url': verification_url,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
    }
    
    html_content = render_email_template('email_verification', context)
    if html_content:
        subject = 'Verify Your Email Address'
        text_content = f"""
Welcome to Reserve With Ease!

Please verify your email address by visiting:
{verification_url}

This link will expire in 24 hours.
        """
        return send_html_email(subject, html_content, [user.email], text_content)
    return False


def send_welcome_email(user):
    """Send welcome email using template"""
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://reserve-with-ease.com')
    context = {
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'user_role': user.role,
        'frontend_url': frontend_url,
    }
    
    html_content = render_email_template('welcome', context)
    if html_content:
        subject = 'Welcome to Reserve With Ease!'
        text_content = f"""
Welcome to Reserve With Ease, {user.first_name}!

Thank you for joining our community! Your account has been successfully created.

{'You can now log in to your owner dashboard and start listing your properties.' if user.role == 'owner' else 'You can now browse and book amazing properties.'}

{'Owner Dashboard: ' + frontend_url + '/owner/dashboard' if user.role == 'owner' else 'Browse Properties: ' + frontend_url + '/properties'}

Best regards,
The Reserve With Ease Team
        """
        return send_html_email(subject, html_content, [user.email], text_content)
    return False


def send_password_reset_email(user, reset_url):
    """Send password reset email using template"""
    context = {
        'reset_url': reset_url,
        'email': user.email,
    }
    
    html_content = render_email_template('password_reset', context)
    if html_content:
        subject = 'Reset Your Password'
        text_content = f"""
Password Reset Request

We received a request to reset your password. Click the link below to create a new password:
{reset_url}

This link will expire in 1 hour for your security.
        """
        return send_html_email(subject, html_content, [user.email], text_content)
    return False


def generate_email_content(template_type, template_data):
    """
    Generate email content using frontend template service or fallback
    """
    try:
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        email_service_url = f"{frontend_url}/api/email/generate"
        
        response = requests.post(
            email_service_url,
            json={'type': template_type, 'data': template_data},
            timeout=10,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            email_data = response.json()
            return (
                email_data.get('html', ''),
                email_data.get('text', ''),
                email_data.get('subject', f'Reserve With Ease - {template_type}')
            )
    except Exception as e:
        print(f"Error calling frontend email service: {e}")
    
    # Fallback to basic HTML generation
    if template_type == 'booking-confirmation':
        subject = f"Booking Confirmed - {template_data.get('propertyName', 'Property')}"
    elif template_type == 'owner-notification':
        subject = f"New Booking - {template_data.get('propertyName', 'Property')}"
    elif template_type == 'email-verification':
        subject = 'Verify Your Email Address'
    elif template_type == 'password-reset':
        subject = 'Reset Your Password'
    elif template_type == 'welcome':
        subject = 'Welcome to Reserve With Ease'
    elif template_type == 'review-response':
        subject = f"Response to Your Review - {template_data.get('propertyName', 'Property')}"
    else:
        subject = 'Reserve With Ease Notification'
    
    # Generate basic HTML fallback
    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2>{subject}</h2>
        <p>This is a {template_type} notification from Reserve With Ease.</p>
        <p>Template data: {json.dumps(template_data, indent=2)}</p>
    </div>
    """
    
    text_content = f"{subject}\n\nThis is a {template_type} notification from Reserve With Ease."
    
    return html_content, text_content, subject


def send_booking_confirmation_email(reservation):
    """Send booking confirmation email to guest"""
    # Prepare context for template
    context = {
        'guest_first_name': reservation.guest_first_name,
        'property_name': reservation.property_obj.name,
        'room_name': reservation.room.name if reservation.room else None,
        'check_in': reservation.check_in.strftime('%Y-%m-%d'),
        'check_out': reservation.check_out.strftime('%Y-%m-%d'),
        'guests': reservation.guests,
        'total_price': reservation.total_price,
        'reservation_id': str(reservation.id),
        'recipient_email': reservation.guest_email,
    }
    
    # Render HTML template
    html_content = render_email_template('booking_confirmation', context)
    
    if html_content:
        subject = f"Booking Confirmed - {reservation.property_obj.name}"
    else:
        # Fallback if template not found
        subject = f"Booking Confirmed - {reservation.property_obj.name}"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>Booking Confirmed!</h2>
            <p>Dear {reservation.guest_first_name},</p>
            <p>Your booking at <strong>{reservation.property_obj.name}</strong> has been confirmed.</p>
        </div>
        """
    
    # Plain text version
    text_content = f"""
BOOKING CONFIRMED!

Dear {reservation.guest_first_name},

Your booking at {reservation.property_obj.name} has been confirmed.

Property: {reservation.property_obj.name}
Check-in: {reservation.check_in}
Check-out: {reservation.check_out}
Guests: {reservation.guests}
Total Price: ₦{reservation.total_price}
Reservation ID: {reservation.id}

Thank you for choosing Reserve With Ease!
    """
    
    # Create email notification
    email_notification = EmailNotification.objects.create(
        recipient=reservation.guest_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    # Send immediately
    email_notification.send()
    
    return email_notification


def send_owner_booking_notification(reservation):
    """Send booking notification to property owner"""
    # Prepare context for template
    context = {
        'owner_name': f"{reservation.property_obj.owner.first_name} {reservation.property_obj.owner.last_name}",
        'guest_first_name': reservation.guest_first_name,
        'guest_last_name': reservation.guest_last_name,
        'guest_email': reservation.guest_email,
        'guest_phone': reservation.guest_phone,
        'property_name': reservation.property_obj.name,
        'check_in': reservation.check_in.strftime('%Y-%m-%d'),
        'check_out': reservation.check_out.strftime('%Y-%m-%d'),
        'guests': reservation.guests,
        'total_price': reservation.total_price,
        'reservation_id': str(reservation.id),
    }
    
    # Render HTML template
    html_content = render_email_template('owner_booking_notification', context)
    
    if html_content:
        subject = f"New Booking - {reservation.property_obj.name}"
    else:
        # Fallback if template not found
        subject = f"New Booking - {reservation.property_obj.name}"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <h2>New Booking Received!</h2>
            <p>Hello {reservation.property_obj.owner.first_name},</p>
            <p>You have received a new booking for <strong>{reservation.property_obj.name}</strong>.</p>
        </div>
        """
    
    # Plain text version
    text_content = f"""
NEW BOOKING RECEIVED!

Hello {reservation.property_obj.owner.first_name} {reservation.property_obj.owner.last_name},

You have received a new booking for {reservation.property_obj.name}.

Guest: {reservation.guest_first_name} {reservation.guest_last_name}
Email: {reservation.guest_email}
Check-in: {reservation.check_in}
Check-out: {reservation.check_out}
Guests: {reservation.guests}
Total Price: ₦{reservation.total_price}

Please respond within 24 hours.
    """
    
    # Create email notification
    email_notification = EmailNotification.objects.create(
        recipient=reservation.property_obj.owner.email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
    )
    
    # Send immediately
    email_notification.send()
    
    return email_notification


def send_review_response_notification(review):
    """Send notification when owner responds to review"""
    # Get the latest response for this review
    try:
        response_obj = review.response_obj
        response_content = response_obj.content
    except:
        # Fallback if no response found
        return None
    
    try:
        template = EmailTemplate.objects.get(
            template_type='review_response',
            is_active=True
        )
    except EmailTemplate.DoesNotExist:
        # Fallback to basic email
        subject = f"Response to Your Review - {review.property_obj.name}"
        html_content = f"""
        <h2>Review Response</h2>
        <p>Dear {review.user.first_name},</p>
        <p>The owner of {review.property_obj.name} has responded to your review:</p>
        <blockquote>{response_content}</blockquote>
        <p>Thank you for your feedback!</p>
        """
        text_content = f"""
        Review Response

        Dear {review.user.first_name},

        The owner of {review.property_obj.name} has responded to your review:

        {response_content}

        Thank you for your feedback!
        """
    else:
        # Use template
        context = {
            'review': review,
            'property': review.property_obj,
            'user': review.user,
            'response': response_obj,
        }
        subject = template.subject
        html_content = render_to_string('emails/review_response.html', context)
        text_content = render_to_string('emails/review_response.txt', context)
    
    # Create email notification
    email_notification = EmailNotification.objects.create(
        recipient=review.user.email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        template=template if 'template' in locals() else None
    )
    
    # Send immediately
    email_notification.send()
    
    return email_notification


def create_notification(user, notification_type, title, message, action_url='', related_object=None):
    """Create an in-app notification"""
    notification = Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
        action_url=action_url,
        related_object_type=related_object.__class__.__name__ if related_object else '',
        related_object_id=related_object.id if related_object else None
    )
    return notification


def send_booking_notifications(reservation):
    """Send all booking-related notifications"""
    # Email to guest
    send_booking_confirmation_email(reservation)
    
    # Email to owner
    send_owner_booking_notification(reservation)
    
    # In-app notification to owner
    create_notification(
        user=reservation.property_obj.owner,
        notification_type='booking_confirmed',
        title='New Booking Received',
        message=f'You have received a new booking for {reservation.property_obj.name} from {reservation.guest_first_name} {reservation.guest_last_name}.',
        action_url=f'/owner/reservations/{reservation.id}',
        related_object=reservation
    )
    
    # In-app notification to guest
    create_notification(
        user=reservation.user,
        notification_type='booking_confirmed',
        title='Booking Confirmed',
        message=f'Your booking at {reservation.property_obj.name} has been confirmed.',
        action_url=f'/user/reservations/{reservation.id}',
        related_object=reservation
    )
