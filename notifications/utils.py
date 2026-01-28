from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from .models import EmailTemplate, EmailNotification, Notification


def send_booking_confirmation_email(reservation):
    """Send booking confirmation email to guest"""
    try:
        template = EmailTemplate.objects.get(
            template_type='booking_confirmation',
            is_active=True
        )
    except EmailTemplate.DoesNotExist:
        # Fallback to basic email
        subject = f"Booking Confirmation - {reservation.property.name}"
        html_content = f"""
        <h2>Booking Confirmed!</h2>
        <p>Dear {reservation.guest_first_name} {reservation.guest_last_name},</p>
        <p>Your booking at {reservation.property.name} has been confirmed.</p>
        <p><strong>Check-in:</strong> {reservation.check_in}</p>
        <p><strong>Check-out:</strong> {reservation.check_out}</p>
        <p><strong>Total Price:</strong> ₦{reservation.total_price}</p>
        <p>Thank you for choosing Reserve at Ease!</p>
        """
        text_content = f"""
        Booking Confirmed!

        Dear {reservation.guest_first_name} {reservation.guest_last_name},

        Your booking at {reservation.property.name} has been confirmed.

        Check-in: {reservation.check_in}
        Check-out: {reservation.check_out}
        Total Price: ₦{reservation.total_price}

        Thank you for choosing Reserve at Ease!
        """
    else:
        # Use template
        context = {
            'reservation': reservation,
            'property': reservation.property,
            'room': reservation.room,
            'user': reservation.user,
        }
        subject = template.subject
        html_content = render_to_string('emails/booking_confirmation.html', context)
        text_content = render_to_string('emails/booking_confirmation.txt', context)

    # Create email notification
    email_notification = EmailNotification.objects.create(
        recipient=reservation.guest_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        template=template if 'template' in locals() else None
    )

    # Send immediately (in production, this should be queued)
    email_notification.send()

    return email_notification


def send_owner_booking_notification(reservation):
    """Send booking notification to property owner"""
    try:
        template = EmailTemplate.objects.get(
            template_type='owner_booking_notification',
            is_active=True
        )
    except EmailTemplate.DoesNotExist:
        # Fallback to basic email
        subject = f"New Booking - {reservation.property.name}"
        html_content = f"""
        <h2>New Booking Received!</h2>
        <p>You have received a new booking for {reservation.property.name}.</p>
        <p><strong>Guest:</strong> {reservation.guest_first_name} {reservation.guest_last_name}</p>
        <p><strong>Email:</strong> {reservation.guest_email}</p>
        <p><strong>Phone:</strong> {reservation.guest_phone}</p>
        <p><strong>Check-in:</strong> {reservation.check_in}</p>
        <p><strong>Check-out:</strong> {reservation.check_out}</p>
        <p><strong>Guests:</strong> {reservation.guests}</p>
        <p><strong>Total Price:</strong> ₦{reservation.total_price}</p>
        <p>Please confirm this booking in your dashboard.</p>
        """
        text_content = f"""
        New Booking Received!

        You have received a new booking for {reservation.property.name}.

        Guest: {reservation.guest_first_name} {reservation.guest_last_name}
        Email: {reservation.guest_email}
        Phone: {reservation.guest_phone}
        Check-in: {reservation.check_in}
        Check-out: {reservation.check_out}
        Guests: {reservation.guests}
        Total Price: ₦{reservation.total_price}

        Please confirm this booking in your dashboard.
        """
    else:
        # Use template
        context = {
            'reservation': reservation,
            'property': reservation.property,
            'room': reservation.room,
            'owner': reservation.property.owner,
        }
        subject = template.subject
        html_content = render_to_string('emails/owner_booking_notification.html', context)
        text_content = render_to_string('emails/owner_booking_notification.txt', context)

    # Create email notification
    email_notification = EmailNotification.objects.create(
        recipient=reservation.property.owner.email,
        subject=subject,
        html_content=html_content,
        text_content=text_content,
        template=template if 'template' in locals() else None
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
        user=reservation.property.owner,
        notification_type='booking_confirmed',
        title='New Booking Received',
        message=f'You have received a new booking for {reservation.property.name} from {reservation.guest_first_name} {reservation.guest_last_name}.',
        action_url=f'/owner/reservations/{reservation.id}',
        related_object=reservation
    )

    # In-app notification to guest
    create_notification(
        user=reservation.user,
        notification_type='booking_confirmed',
        title='Booking Confirmed',
        message=f'Your booking at {reservation.property.name} has been confirmed.',
        action_url=f'/user/reservations/{reservation.id}',
        related_object=reservation
    )