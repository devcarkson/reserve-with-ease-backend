from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import PropertyType
from .utils import convert_r2_url_to_public


@receiver(post_save, sender=PropertyType)
def update_property_type_image_url(sender, instance, created, **kwargs):
    """Update image_url when image is uploaded or changed"""
    if instance.image:
        image_name = instance.image.name
        r2_url = convert_r2_url_to_public(image_name)
        if instance.image_url != r2_url:
            PropertyType.objects.filter(pk=instance.pk).update(image_url=r2_url)
