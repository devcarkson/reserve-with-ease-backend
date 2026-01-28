from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from properties.models import Property

User = get_user_model()

class Command(BaseCommand):
    help = 'Populate database with 10 sample properties for decarkson@gmail.com'

    def handle(self, *args, **options):
        try:
            owner = User.objects.get(email='decarkson@gmail.com')
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR('User with email decarkson@gmail.com does not exist')
            )
            return

        properties_data = [
            {
                'name': 'Luxury Beach Resort Lagos',
                'type': 'resort',
                'city': 'Lagos',
                'country': 'Nigeria',
                'address': 'Victoria Island, Lagos',
                'latitude': 6.4474,
                'longitude': 3.3903,
                'price_per_night': 25000.00,
                'currency': 'NGN',
                'description': 'A luxurious beach resort with stunning ocean views, private beach access, and world-class amenities.',
                'amenities': ['WiFi', 'Pool', 'Spa', 'Restaurant', 'Bar', 'Parking', 'Air Conditioning'],
                'highlights': ['Ocean View', 'Private Beach', 'Spa Services', 'Fine Dining'],
                'free_cancellation': True,
                'breakfast_included': True,
                'featured': True,
                'map_link': 'https://maps.google.com/?q=Victoria+Island+Lagos',
                'check_in_time': '14:00',
                'check_out_time': '11:00',
                'express_check_in': True,
                'cancellation_policy': [
                    'Free cancellation up to 24 hours before check-in',
                    '50% refund for cancellations 24-72 hours before check-in',
                    'No refund for cancellations less than 24 hours before check-in'
                ],
                'house_rules': [
                    'Check-in after 2:00 PM',
                    'Check-out before 11:00 AM',
                    'No smoking in rooms',
                    'Pets allowed with permission'
                ],
                'contacts': [
                    {'name': 'Front Desk', 'phone': '+234 801 234 5678', 'role': 'contact'},
                    {'name': 'Manager', 'phone': '+234 801 234 5679', 'role': 'reservation'}
                ],
                'image_labels': ['Main Entrance', 'Beach View', 'Pool Area', 'Restaurant', 'Spa', 'Room Interior', 'Balcony', 'Garden', 'Lobby', 'Gym'],
                'main_image_index': 0
            },
            {
                'name': 'Boutique Hotel Victoria Island',
                'type': 'hotel',
                'city': 'Lagos',
                'country': 'Nigeria',
                'address': 'Adeola Odeku Street, Victoria Island',
                'latitude': 6.4281,
                'longitude': 3.4219,
                'price_per_night': 18000.00,
                'currency': 'NGN',
                'description': 'A stylish boutique hotel in the heart of Victoria Island, offering modern comfort and convenience.',
                'amenities': ['WiFi', 'Gym', 'Restaurant', 'Room Service', 'Business Center', 'Air Conditioning'],
                'highlights': ['City Center Location', 'Modern Design', 'Business Facilities', '24/7 Service'],
                'free_cancellation': True,
                'breakfast_included': False,
                'featured': False,
                'map_link': 'https://maps.google.com/?q=Adeola+Odeku+Victoria+Island',
                'check_in_time': '15:00',
                'check_out_time': '12:00',
                'express_check_in': False,
                'cancellation_policy': [
                    'Free cancellation up to 48 hours before check-in',
                    'Full refund for cancellations made 7+ days before check-in'
                ],
                'house_rules': [
                    'Quiet hours 10:00 PM - 6:00 AM',
                    'No outside guests without permission'
                ],
                'contacts': [
                    {'name': 'Concierge', 'phone': '+234 802 345 6789', 'role': 'contact'}
                ],
                'image_labels': ['Hotel Exterior', 'Lobby', 'Standard Room', 'Deluxe Room', 'Restaurant', 'Business Center', 'Gym', 'City View', 'Bar', 'Roof Terrace'],
                'main_image_index': 0
            },
            {
                'name': 'Abuja Presidential Hotel',
                'type': 'hotel',
                'city': 'Abuja',
                'country': 'Nigeria',
                'address': 'Central Business District, Abuja',
                'latitude': 9.0765,
                'longitude': 7.3986,
                'price_per_night': 22000.00,
                'currency': 'NGN',
                'description': 'A prestigious hotel in the heart of Abuja, offering luxury accommodations and excellent service.',
                'amenities': ['WiFi', 'Pool', 'Gym', 'Restaurant', 'Bar', 'Parking', 'Air Conditioning', 'Business Center'],
                'highlights': ['CBD Location', 'Presidential Suites', 'Conference Facilities', 'Luxury Amenities'],
                'free_cancellation': False,
                'breakfast_included': True,
                'featured': True,
                'map_link': 'https://maps.google.com/?q=Central+Business+District+Abuja',
                'check_in_time': '14:00',
                'check_out_time': '11:00',
                'express_check_in': True,
                'cancellation_policy': [
                    'Cancellation policy varies by rate',
                    'Contact hotel directly for cancellations'
                ],
                'house_rules': [
                    'Government officials receive priority',
                    'Formal attire required in public areas'
                ],
                'contacts': [
                    {'name': 'Reservations', 'phone': '+234 803 456 7890', 'role': 'reservation'},
                    {'name': 'Manager', 'phone': '+234 803 456 7891', 'role': 'contact'}
                ],
                'image_labels': ['Main Building', 'Presidential Suite', 'Conference Room', 'Restaurant', 'Pool', 'Gym', 'Lobby', 'City View', 'Bar', 'Spa'],
                'main_image_index': 0
            },
            {
                'name': 'Port Harcourt Business Hotel',
                'type': 'hotel',
                'city': 'Port Harcourt',
                'country': 'Nigeria',
                'address': 'GRA Phase 2, Port Harcourt',
                'latitude': 4.8156,
                'longitude': 7.0498,
                'price_per_night': 15000.00,
                'currency': 'NGN',
                'description': 'A modern business hotel in Port Harcourt, perfect for corporate travelers and business meetings.',
                'amenities': ['WiFi', 'Business Center', 'Meeting Rooms', 'Restaurant', 'Parking', 'Air Conditioning'],
                'highlights': ['Business District', 'Meeting Facilities', 'High-Speed Internet', 'Airport Shuttle'],
                'free_cancellation': True,
                'breakfast_included': True,
                'featured': False,
                'map_link': 'https://maps.google.com/?q=GRA+Phase+2+Port+Harcourt',
                'check_in_time': '12:00',
                'check_out_time': '10:00',
                'express_check_in': False,
                'cancellation_policy': [
                    'Free cancellation up to 24 hours',
                    'Business rates may have different policies'
                ],
                'house_rules': [
                    'Business casual attire preferred',
                    'Meeting rooms available for registered guests'
                ],
                'contacts': [
                    {'name': 'Business Center', 'phone': '+234 804 567 8901', 'role': 'contact'}
                ],
                'image_labels': ['Hotel Entrance', 'Business Lounge', 'Meeting Room', 'Executive Room', 'Restaurant', 'Lobby', 'City View', 'Parking', 'Gym', 'Pool'],
                'main_image_index': 0
            },
            {
                'name': 'Kano Heritage Resort',
                'type': 'resort',
                'city': 'Kano',
                'country': 'Nigeria',
                'description': 'A unique resort blending traditional Hausa architecture with modern comfort, located near ancient city walls.',
                'address': 'Kofar Mata, Kano',
                'latitude': 12.0022,
                'longitude': 8.5919,
                'price_per_night': 12000.00,
                'currency': 'NGN',
                'amenities': ['WiFi', 'Traditional Restaurant', 'Cultural Tours', 'Parking', 'Air Conditioning'],
                'highlights': ['Cultural Heritage', 'Traditional Architecture', 'Local Cuisine', 'Historical Location'],
                'free_cancellation': True,
                'breakfast_included': True,
                'featured': True,
                'map_link': 'https://maps.google.com/?q=Kofar+Mata+Kano',
                'check_in_time': '14:00',
                'check_out_time': '12:00',
                'express_check_in': False,
                'cancellation_policy': [
                    'Free cancellation up to 72 hours before check-in',
                    'Cultural tours may have separate cancellation policies'
                ],
                'house_rules': [
                    'Respect local customs and traditions',
                    'Traditional attire available for cultural events'
                ],
                'contacts': [
                    {'name': 'Cultural Guide', 'phone': '+234 805 678 9012', 'role': 'contact'}
                ],
                'image_labels': ['Traditional Entrance', 'Heritage Building', 'Cultural Hall', 'Restaurant', 'Garden', 'Traditional Room', 'City Wall View', 'Cultural Display', 'Dining Area', 'Reception'],
                'main_image_index': 0
            },
            {
                'name': 'Ibadan University Guesthouse',
                'type': 'hotel',
                'city': 'Ibadan',
                'country': 'Nigeria',
                'address': 'University of Ibadan Campus',
                'latitude': 7.3775,
                'longitude': 3.9470,
                'price_per_night': 8000.00,
                'currency': 'NGN',
                'description': 'Comfortable accommodation for visitors to the University of Ibadan, with easy access to academic facilities.',
                'amenities': ['WiFi', 'Library Access', 'Restaurant', 'Parking', 'Air Conditioning'],
                'highlights': ['University Location', 'Academic Atmosphere', 'Affordable Rates', 'Campus Access'],
                'free_cancellation': True,
                'breakfast_included': True,
                'featured': False,
                'map_link': 'https://maps.google.com/?q=University+of+Ibadan+Campus',
                'check_in_time': '16:00',
                'check_out_time': '10:00',
                'express_check_in': False,
                'cancellation_policy': [
                    'Free cancellation up to 48 hours',
                    'Academic rates available for researchers'
                ],
                'house_rules': [
                    'University ID may be required',
                    'Quiet hours observed',
                    'Library access for registered guests'
                ],
                'contacts': [
                    {'name': 'Guest Services', 'phone': '+234 806 789 0123', 'role': 'contact'}
                ],
                'image_labels': ['Campus View', 'Guesthouse Exterior', 'Standard Room', 'Common Area', 'Dining Hall', 'Library', 'Garden', 'University Buildings', 'Reception', 'Study Area'],
                'main_image_index': 0
            },
            {
                'name': 'Enugu Hills Resort',
                'type': 'resort',
                'city': 'Enugu',
                'country': 'Nigeria',
                'address': 'Hilltop Area, Enugu',
                'latitude': 6.4654,
                'longitude': 7.5464,
                'price_per_night': 16000.00,
                'currency': 'NGN',
                'description': 'A scenic resort located on the hills of Enugu, offering panoramic views and peaceful surroundings.',
                'amenities': ['WiFi', 'Pool', 'Restaurant', 'Parking', 'Air Conditioning', 'Hiking Trails'],
                'highlights': ['Hilltop Location', 'Panoramic Views', 'Peaceful Environment', 'Nature Trails'],
                'free_cancellation': True,
                'breakfast_included': True,
                'featured': True,
                'map_link': 'https://maps.google.com/?q=Hilltop+Area+Enugu',
                'check_in_time': '13:00',
                'check_out_time': '11:00',
                'express_check_in': True,
                'cancellation_policy': [
                    'Free cancellation up to 72 hours',
                    'Scenic view guarantee with select rooms'
                ],
                'house_rules': [
                    'Enjoy the natural surroundings',
                    'Guided hikes available',
                    'Photography encouraged'
                ],
                'contacts': [
                    {'name': 'Activities Coordinator', 'phone': '+234 807 890 1234', 'role': 'contact'}
                ],
                'image_labels': ['Hilltop View', 'Resort Entrance', 'Panoramic Room', 'Pool Area', 'Restaurant', 'Nature Trail', 'Garden', 'Sunset View', 'Lobby', 'Dining Terrace'],
                'main_image_index': 0
            },
            {
                'name': 'Calabar Beachfront Hotel',
                'type': 'hotel',
                'city': 'Calabar',
                'country': 'Nigeria',
                'address': 'Marina Resort Area, Calabar',
                'latitude': 4.9757,
                'longitude': 8.3417,
                'price_per_night': 14000.00,
                'currency': 'NGN',
                'description': 'A beachfront hotel in Calabar, offering stunning views of the Calabar River and Cross River.',
                'amenities': ['WiFi', 'Pool', 'Restaurant', 'Bar', 'Parking', 'Air Conditioning', 'Water Sports'],
                'highlights': ['Beachfront Location', 'River Views', 'Water Activities', 'Tropical Setting'],
                'free_cancellation': True,
                'breakfast_included': False,
                'featured': False,
                'map_link': 'https://maps.google.com/?q=Marina+Resort+Calabar',
                'check_in_time': '15:00',
                'check_out_time': '11:00',
                'express_check_in': False,
                'cancellation_policy': [
                    'Free cancellation up to 48 hours',
                    'Weather-dependent activities'
                ],
                'house_rules': [
                    'Beach safety guidelines must be followed',
                    'Water sports equipment rental available'
                ],
                'contacts': [
                    {'name': 'Activities Desk', 'phone': '+234 808 901 2345', 'role': 'contact'}
                ],
                'image_labels': ['Beach View', 'Hotel Exterior', 'River View', 'Pool', 'Restaurant', 'Water Sports', 'Garden', 'Sunset Deck', 'Lobby', 'Bar'],
                'main_image_index': 0
            },
            {
                'name': 'Jos Plateau Hotel',
                'type': 'hotel',
                'city': 'Jos',
                'country': 'Nigeria',
                'address': 'Jos Plateau, Jos',
                'latitude': 9.8965,
                'longitude': 8.8583,
                'price_per_night': 11000.00,
                'currency': 'NGN',
                'description': 'A comfortable hotel on the Jos Plateau, offering cool climate and proximity to tourist attractions.',
                'amenities': ['WiFi', 'Restaurant', 'Parking', 'Air Conditioning', 'Tour Desk'],
                'highlights': ['Plateau Location', 'Cool Climate', 'Tourist Access', 'Comfortable Stay'],
                'free_cancellation': True,
                'breakfast_included': True,
                'featured': False,
                'map_link': 'https://maps.google.com/?q=Jos+Plateau+Jos',
                'check_in_time': '14:00',
                'check_out_time': '12:00',
                'express_check_in': False,
                'cancellation_policy': [
                    'Free cancellation up to 72 hours',
                    'Tour packages may have different policies'
                ],
                'house_rules': [
                    'Cool weather clothing recommended',
                    'Tour desk available for local attractions'
                ],
                'contacts': [
                    {'name': 'Tour Coordinator', 'phone': '+234 809 012 3456', 'role': 'contact'}
                ],
                'image_labels': ['Plateau View', 'Hotel Building', 'Comfort Room', 'Restaurant', 'Garden', 'Mountain View', 'Reception', 'Dining Area', 'Tour Desk', 'Parking'],
                'main_image_index': 0
            },
            {
                'name': 'Benin City Heritage Hotel',
                'type': 'hotel',
                'city': 'Benin City',
                'country': 'Nigeria',
                'address': 'Ring Road, Benin City',
                'latitude': 6.3392,
                'longitude': 5.6170,
                'price_per_night': 10000.00,
                'currency': 'NGN',
                'description': 'A heritage hotel in Benin City, combining traditional Benin architecture with modern amenities.',
                'amenities': ['WiFi', 'Traditional Restaurant', 'Cultural Center', 'Parking', 'Air Conditioning'],
                'highlights': ['Cultural Heritage', 'Traditional Architecture', 'Local Artifacts', 'Historical Significance'],
                'free_cancellation': True,
                'breakfast_included': True,
                'featured': True,
                'map_link': 'https://maps.google.com/?q=Ring+Road+Benin+City',
                'check_in_time': '14:00',
                'check_out_time': '12:00',
                'express_check_in': False,
                'cancellation_policy': [
                    'Free cancellation up to 48 hours',
                    'Cultural tours included in select packages'
                ],
                'house_rules': [
                    'Respect cultural artifacts',
                    'Photography permitted in designated areas',
                    'Traditional attire available'
                ],
                'contacts': [
                    {'name': 'Cultural Liaison', 'phone': '+234 810 123 4567', 'role': 'contact'}
                ],
                'image_labels': ['Heritage Building', 'Traditional Entrance', 'Cultural Hall', 'Restaurant', 'Artifact Display', 'Garden', 'Traditional Room', 'Reception', 'Dining Area', 'Cultural Performance'],
                'main_image_index': 0
            }
        ]

        created_count = 0
        for prop_data in properties_data:
            # Create property with sample images
            images = [
                'https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800',
                'https://images.unsplash.com/photo-1571003123894-1f0594d2b5d9?w=800',
                'https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800',
                'https://images.unsplash.com/photo-1590490360182-c33d57733427?w=800',
                'https://images.unsplash.com/photo-1564501049412-61c2a3083791?w=800',
                'https://images.unsplash.com/photo-1586023492125-27b2c045efd7?w=800',
                'https://images.unsplash.com/photo-1551882547-ff40c63fe5fa?w=800',
                'https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800',
                'https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?w=800',
                'https://images.unsplash.com/photo-1586375300773-8384e3e4916f?w=800'
            ]

            property = Property.objects.create(
                owner=owner,
                images=images,
                **prop_data
            )
            created_count += 1
            self.stdout.write(
                self.style.SUCCESS(f'Created property: {property.name}')
            )

        self.stdout.write(
            self.style.SUCCESS(f'Successfully created {created_count} properties for {owner.email}')
        )