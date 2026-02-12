#!/usr/bin/env python
"""
Script to populate original_price and discount_percentage for existing reservations.
Run this after adding the new fields to the model.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'reserve_at_ease.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from reservations.models import Reservation
from django.utils import timezone

def populate_discounts():
    """Populate original_price and discount_percentage for existing reservations."""
    reservations = Reservation.objects.all()
    updated_count = 0
    
    for reservation in reservations:
        nights = (reservation.check_out - reservation.check_in).days
        
        # Calculate base price from room_category or room
        if reservation.room_category:
            base_price = float(reservation.room_category.base_price)
            # Check if discount was active at the time of booking
            if reservation.room_category.has_discount:
                if reservation.room_category.discount_start_date and reservation.room_category.discount_end_date:
                    if reservation.room_category.discount_start_date <= reservation.created_at.date() <= reservation.room_category.discount_end_date:
                        discount_percentage = float(reservation.room_category.discount_percentage) if reservation.room_category.discount_percentage else 0
                        effective_price = base_price * (1 - discount_percentage / 100)
                        total_price = effective_price * nights
                    else:
                        discount_percentage = 0
                        total_price = base_price * nights
                else:
                    discount_percentage = 0
                    total_price = base_price * nights
            else:
                discount_percentage = 0
                total_price = base_price * nights
        elif reservation.room:
            base_price = float(reservation.room.price_per_night)
            discount_percentage = 0
            total_price = base_price * nights
        else:
            # No room or category, skip
            continue
        
        # Update the reservation if values differ
        if (reservation.original_price or 0) != (base_price * nights) or \
           (reservation.discount_percentage or 0) != discount_percentage:
            
            reservation.original_price = base_price * nights
            reservation.discount_percentage = discount_percentage
            # Also update total_price if it doesn't match
            if float(reservation.total_price) != total_price:
                reservation.total_price = total_price
                
            reservation.save()
            updated_count += 1
            print(f"Updated reservation {reservation.id}: original_price={base_price * nights}, discount_percentage={discount_percentage}")
    
    print(f"\nTotal reservations updated: {updated_count}")

if __name__ == '__main__':
    populate_discounts()
