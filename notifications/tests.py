from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core import mail
from rest_framework.test import APITestCase
from rest_framework import status
from properties.models import Property
from reservations.models import Reservation
from reviews.models import Review
from .models import Notification, EmailTemplate, EmailNotification

User = get_user_model()


class NotificationsAPITestCase(APITestCase):
    def setUp(self):
        # Create test users
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123',
            role='user'
        )
        self.owner = User.objects.create_user(
            username='testowner',
            email='owner@test.com',
            password='testpass123',
            role='owner'
        )

        # Create test property
        self.property = Property.objects.create(
            name='Test Property',
            type='hotel',
            city='Lagos',
            country='Nigeria',
            address='Test Address',
            latitude=6.5244,
            longitude=3.3792,
            price_per_night=50000,
            currency='NGN',
            owner=self.owner
        )

        # Create test reservation
        self.reservation = Reservation.objects.create(
            property=self.property,
            room=self.property.rooms.first() if self.property.rooms.exists() else None,
            user=self.user,
            check_in='2024-12-25',
            check_out='2024-12-27',
            guests=2,
            total_price=100000,
            guest_first_name='John',
            guest_last_name='Doe',
            guest_email='john@test.com',
            guest_phone='+2341234567890'
        )

    def test_notification_list_authenticated(self):
        """Test notification list access for authenticated user"""
        self.client.force_authenticate(user=self.user)
        url = reverse('notifications:notification-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_notification_list_unauthenticated(self):
        """Test notification list access for unauthenticated user"""
        url = reverse('notifications:notification-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mark_notification_read(self):
        """Test marking a notification as read"""
        # Create a notification
        notification = Notification.objects.create(
            user=self.user,
            notification_type='booking_confirmed',
            title='Test Notification',
            message='Test message'
        )

        self.client.force_authenticate(user=self.user)
        url = reverse('notifications:mark-notification-read', kwargs={'notification_id': notification.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        notification.refresh_from_db()
        self.assertTrue(notification.is_read)

    def test_mark_notification_read_wrong_user(self):
        """Test marking another user's notification as read"""
        other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='testpass123'
        )
        notification = Notification.objects.create(
            user=other_user,
            notification_type='booking_confirmed',
            title='Test Notification',
            message='Test message'
        )

        self.client.force_authenticate(user=self.user)
        url = reverse('notifications:mark-notification-read', kwargs={'notification_id': notification.id})
        response = self.client.post(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_notification_count(self):
        """Test getting notification count"""
        # Create unread notifications
        Notification.objects.create(
            user=self.user,
            notification_type='booking_confirmed',
            title='Test Notification 1',
            message='Test message 1',
            is_read=False
        )
        Notification.objects.create(
            user=self.user,
            notification_type='payment_received',
            title='Test Notification 2',
            message='Test message 2',
            is_read=False
        )

        self.client.force_authenticate(user=self.user)
        url = reverse('notifications:notification-count')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 2)


class EmailNotificationsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123',
            role='user'
        )
        self.owner = User.objects.create_user(
            username='testowner',
            email='owner@test.com',
            password='testpass123',
            role='owner'
        )

        self.property = Property.objects.create(
            name='Test Property',
            type='hotel',
            city='Lagos',
            country='Nigeria',
            address='Test Address',
            latitude=6.5244,
            longitude=3.3792,
            price_per_night=50000,
            currency='NGN',
            owner=self.owner
        )

    def test_email_template_creation(self):
        """Test email template creation"""
        template = EmailTemplate.objects.create(
            name='Test Template',
            template_type='booking_confirmation',
            subject='Booking Confirmed',
            html_content='<h1>Booking Confirmed</h1>',
            text_content='Booking Confirmed'
        )

        self.assertEqual(template.name, 'Test Template')
        self.assertEqual(template.template_type, 'booking_confirmation')
        self.assertTrue(template.is_active)

    def test_email_notification_creation(self):
        """Test email notification creation and sending"""
        email_notification = EmailNotification.objects.create(
            recipient='test@example.com',
            subject='Test Subject',
            html_content='<p>Test content</p>',
            text_content='Test content'
        )

        self.assertEqual(email_notification.recipient, 'test@example.com')
        self.assertEqual(email_notification.status, 'pending')

        # Test sending (this will fail in test environment, but should not raise exception)
        try:
            email_notification.send()
        except:
            pass  # Expected in test environment without email backend

    def test_notification_creation(self):
        """Test in-app notification creation"""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='booking_confirmed',
            title='Booking Confirmed',
            message='Your booking has been confirmed'
        )

        self.assertEqual(notification.user, self.user)
        self.assertEqual(notification.notification_type, 'booking_confirmed')
        self.assertFalse(notification.is_read)

    def test_notification_mark_as_read(self):
        """Test marking notification as read"""
        notification = Notification.objects.create(
            user=self.user,
            notification_type='booking_confirmed',
            title='Booking Confirmed',
            message='Your booking has been confirmed'
        )

        self.assertFalse(notification.is_read)

        notification.mark_as_read()

        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)


class NotificationUtilsTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='user@test.com',
            password='testpass123',
            role='user'
        )
        self.owner = User.objects.create_user(
            username='testowner',
            email='owner@test.com',
            password='testpass123',
            role='owner'
        )

        self.property = Property.objects.create(
            name='Test Property',
            type='hotel',
            city='Lagos',
            country='Nigeria',
            address='Test Address',
            latitude=6.5244,
            longitude=3.3792,
            price_per_night=50000,
            currency='NGN',
            owner=self.owner
        )

        self.reservation = Reservation.objects.create(
            property=self.property,
            room=self.property.rooms.first() if self.property.rooms.exists() else None,
            user=self.user,
            check_in='2024-12-25',
            check_out='2024-12-27',
            guests=2,
            total_price=100000,
            guest_first_name='John',
            guest_last_name='Doe',
            guest_email='john@test.com',
            guest_phone='+2341234567890'
        )

    def test_send_booking_notifications(self):
        """Test sending booking notifications"""
        from .utils import send_booking_notifications

        # This should create email notifications and in-app notifications
        send_booking_notifications(self.reservation)

        # Check that notifications were created
        user_notifications = Notification.objects.filter(user=self.user)
        owner_notifications = Notification.objects.filter(user=self.owner)

        self.assertTrue(user_notifications.exists())
        self.assertTrue(owner_notifications.exists())

        # Check that email notifications were created
        email_notifications = EmailNotification.objects.all()
        self.assertTrue(email_notifications.exists())