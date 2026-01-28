from django.core.management.base import BaseCommand
from properties.models import Room, RoomCategory

class Command(BaseCommand):
    help = 'Fix room names by removing " - Room X" suffixes and link to categories'

    def handle(self, *args, **options):
        updated_count = 0
        for room in Room.objects.all():
            if ' - Room ' in room.name:
                base_name = room.name.split(' - Room ')[0]
                room.name = base_name

                # Try to find or create category
                category, created = RoomCategory.objects.get_or_create(
                    property=room.property,
                    name=base_name,
                    defaults={
                        'description': f'{base_name} room category',
                        'base_price': room.price_per_night,
                        'max_occupancy': room.max_guests,
                        'bed_type': room.bed_type,
                        'size': room.size,
                        'amenities': room.amenities
                    }
                )
                room.room_category = category
                room.save()
                updated_count += 1
                self.stdout.write(f'Updated room {room.id}: {base_name} (category: {category.name})')

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} rooms'))