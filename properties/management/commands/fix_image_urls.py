from django.core.management.base import BaseCommand
from properties.models import Property


class Command(BaseCommand):
    help = 'Fix existing image URLs to use public R2 URL format'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be changed without making changes',
        )

    def handle(self, *args, **options):
        R2_PUBLIC_URL = 'https://pub-55e6e691913e44f98f71163828507001.r2.dev'
        OLD_R2_ENDPOINT = '974dd2fd587f660b7a5b75ca1057b741.r2.cloudflarestorage.com'
        
        def convert_url(url):
            """Convert URL to public R2 format"""
            if not url:
                return url
            
            # Already using public R2 URL
            if 'pub-' in url and 'r2.dev' in url:
                return url
            
            # Has old R2 endpoint - remove it and prepend R2 public URL
            if OLD_R2_ENDPOINT in url:
                url = url.replace(f'https://{OLD_R2_ENDPOINT}', '')
                url = url.lstrip('/')
                return f'{R2_PUBLIC_URL}/{url}'
            
            # Is a relative path (starts with property_images/, profile_pics/, room_images/)
            if url.startswith(('property_images/', 'profile_pics/', 'room_images/')):
                return f'{R2_PUBLIC_URL}/{url}'
            
            # Is a local media path (contains localhost or /media/)
            if 'localhost' in url:
                # Extract path after the domain and port
                # http://localhost:8000/media/property_images/... -> property_images/...
                url = url.split('localhost')[1]
                # Remove port if present (:8000)
                if url.startswith(':'):
                    url = url[url.find('/'):]
                url = url.lstrip('/')
                # Remove 'media/' prefix
                url = url.replace('media/', '', 1)
                return f'{R2_PUBLIC_URL}/{url}'
            
            # Is a /media/ path
            if url.startswith('/media/'):
                url = url.replace('/media/', '', 1)
                return f'{R2_PUBLIC_URL}/{url}'
            
            # For any other URL (like unsplash), return as-is
            return url
        
        # Fix Property images
        fixed_count = 0
        for prop in Property.objects.all():
            if prop.images:
                new_images = []
                changed = False
                for img_url in prop.images:
                    original = img_url
                    converted = convert_url(img_url)
                    if converted != original:
                        changed = True
                        self.stdout.write(f'  {original}')
                        self.stdout.write(f'  -> {converted}')
                    new_images.append(converted)
                
                if changed:
                    if not options['dry_run']:
                        prop.images = new_images
                        prop.save()
                    fixed_count += 1
                    self.stdout.write(self.style.WARNING(f'Property #{prop.id}: {prop.name}'))
        
        if fixed_count > 0:
            if options['dry_run']:
                self.stdout.write(self.style.WARNING(f'Dry run: Would fix {fixed_count} properties'))
            else:
                self.stdout.write(self.style.SUCCESS(f'Fixed {fixed_count} properties'))
        else:
            self.stdout.write(self.style.SUCCESS('No properties needed fixing'))
