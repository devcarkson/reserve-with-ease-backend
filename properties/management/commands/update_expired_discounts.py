from django.core.management.base import BaseCommand
from django.utils import timezone
from properties.models import Property

class Command(BaseCommand):
    help = 'Update expired discounts for all properties'

    def handle(self, *args, **options):
        now = timezone.now()
        
        # Find and update properties with expired discounts
        expired = Property.objects.filter(
            has_discount=True,
            discount_end_date__lt=now
        )
        
        count = expired.count()
        expired.update(
            has_discount=False,
            discount_percentage=0,
            discount_start_date=None,
            discount_end_date=None
        )
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {count} expired discounts')
        )
