import os
import sys
import django
from datetime import datetime, timedelta

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserve_at_ease.settings')
django.setup()

from properties.models import Property, RoomCategory, PropertyAvailability
from django.contrib.auth import get_user_model

User = get_user_model()

def add_sample_discounts():
    """Add sample discounts to test the discount functionality"""
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='test_owner',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'Owner'
        }
    )
    
    # Get first property or create a sample one
    property = Property.objects.first()
    if not property:
        print("No properties found. Please create a property first.")
        return
    
    print(f"Adding discounts to property: {property.name}")
    
    # Create a room category with discount
    room_category, created = RoomCategory.objects.get_or_create(
        property=property,
        name='Deluxe Room with Discount',
        defaults={
            'description': 'A luxurious room with special weekend discount',
            'base_price': 15000.00,
            'max_occupancy': 2,
            'bed_type': 'Queen',
            'size': 30,
            'amenities': ['WiFi', 'Air Conditioning', 'Mini Bar', 'TV'],
            'has_discount': True,
            'discount_percentage': 25.00,
            'discount_start_date': datetime.now().date(),
            'discount_end_date': (datetime.now() + timedelta(days=30)).date(),
        }
    )
    
    if created:
        print(f"Created room category: {room_category.name}")
        print(f"Base price: ₦{room_category.base_price}")
        print(f"Discount: {room_category.discount_percentage}%")
        print(f"Effective price: ₦{room_category.get_effective_price()}")
    else:
        # Update existing category to have discount
        room_category.has_discount = True
        room_category.discount_percentage = 25.00
        room_category.discount_start_date = datetime.now().date()
        room_category.discount_end_date = (datetime.now() + timedelta(days=30)).date()
        room_category.save()
        print(f"Updated room category with discount: {room_category.name}")
    
    # Add some calendar discounts for specific dates
    today = datetime.now().date()
    for i in range(7):  # Add discounts for next 7 days
        date = today + timedelta(days=i)
        
        availability, created = PropertyAvailability.objects.get_or_create(
            property=property,
            date=date,
            defaults={
                'available': True,
                'price': 12000.00,  # Lower price for weekends
                'minimum_stay': 1,
                'has_discount': True,
                'discount_percentage': 20.00 if i >= 5 else 15.00,  # Higher discount on weekends
            }
        )
        
        if created:
            print(f"Created discounted availability for {date}: {availability.discount_percentage}% off")
        else:
            # Update existing to have discount
            availability.has_discount = True
            availability.discount_percentage = 20.00 if i >= 5 else 15.00
            availability.save()
            print(f"Updated availability for {date}: {availability.discount_percentage}% off")
    
    print("\nSample discounts added successfully!")
    print(f"Property ID: {property.id}")
    print(f"Room Category ID: {room_category.id}")
    print("\nYou can now test the discount functionality in the frontend.")

if __name__ == '__main__':
    add_sample_discounts()
