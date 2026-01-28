from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from properties.models import Property
from reservations.models import Reservation
from reviews.models import Review
from .models import UserDashboardStats, OwnerDashboardStats, AdminDashboardStats

User = get_user_model()


class DashboardAPITestCase(APITestCase):
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
        self.admin = User.objects.create_user(
            username='testadmin',
            email='admin@test.com',
            password='testpass123',
            role='admin'
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

    def test_user_dashboard_authenticated(self):
        """Test user dashboard access for authenticated user"""
        self.client.force_authenticate(user=self.user)
        url = reverse('dashboard:user-dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_reservations', response.data)
        self.assertIn('total_spent', response.data)

    def test_user_dashboard_unauthenticated(self):
        """Test user dashboard access for unauthenticated user"""
        url = reverse('dashboard:user-dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_owner_dashboard_authenticated(self):
        """Test owner dashboard access for authenticated owner"""
        self.client.force_authenticate(user=self.owner)
        url = reverse('dashboard:owner-dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_properties', response.data)
        self.assertIn('total_revenue', response.data)

    def test_owner_dashboard_wrong_role(self):
        """Test owner dashboard access for user with wrong role"""
        self.client.force_authenticate(user=self.user)
        url = reverse('dashboard:owner-dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_dashboard_authenticated(self):
        """Test admin dashboard access for authenticated admin"""
        self.client.force_authenticate(user=self.admin)
        url = reverse('dashboard:admin-dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_users', response.data)
        self.assertIn('total_properties', response.data)

    def test_admin_dashboard_wrong_role(self):
        """Test admin dashboard access for user with wrong role"""
        self.client.force_authenticate(user=self.user)
        url = reverse('dashboard:admin-dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class DashboardStatsTestCase(TestCase):
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

    def test_user_dashboard_stats_creation(self):
        """Test that user dashboard stats are created properly"""
        stats = UserDashboardStats.objects.create(user=self.user)

        # Check initial values
        self.assertEqual(stats.total_reservations, 0)
        self.assertEqual(stats.total_spent, 0)
        self.assertEqual(stats.upcoming_reservations, 0)

    def test_owner_dashboard_stats_creation(self):
        """Test that owner dashboard stats are created properly"""
        stats = OwnerDashboardStats.objects.create(owner=self.owner)

        # Check initial values
        self.assertEqual(stats.total_properties, 0)
        self.assertEqual(stats.total_reservations, 0)
        self.assertEqual(stats.total_revenue, 0)

    def test_admin_dashboard_stats_creation(self):
        """Test that admin dashboard stats are created properly"""
        from django.utils import timezone
        today = timezone.now().date()
        stats = AdminDashboardStats.objects.create(date=today)

        # Check initial values
        self.assertEqual(stats.total_users, 0)
        self.assertEqual(stats.total_properties, 0)
        self.assertEqual(stats.total_reservations, 0)
