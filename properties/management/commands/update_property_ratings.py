from django.core.management.base import BaseCommand
from django.db.models import Avg
from properties.models import Property
from reviews.models import Review


class Command(BaseCommand):
    help = 'Update property ratings and review counts based on approved reviews'

    def handle(self, *args, **options):
        properties = Property.objects.all()
        updated_count = 0

        for property_obj in properties:
            reviews = Review.objects.filter(property_obj=property_obj, approved=True)

            if reviews.exists():
                avg_rating = reviews.aggregate(avg_rating=Avg('rating'))['avg_rating']
                property_obj.rating = round(avg_rating, 1) if avg_rating else 0
                property_obj.review_count = reviews.count()
            else:
                property_obj.rating = 0
                property_obj.review_count = 0

            property_obj.save()
            updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated ratings for {updated_count} properties')
        )