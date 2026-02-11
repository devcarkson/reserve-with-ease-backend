from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from .models import PropertyType, RoomCategory
from .utils import convert_r2_url_to_public


@receiver(post_save, sender=PropertyType)
def update_property_type_image_url(sender, instance, created, **kwargs):
    """Update image_url when image is uploaded or changed"""
    if instance.image:
        image_name = instance.image.name
        r2_url = convert_r2_url_to_public(image_name)
        if instance.image_url != r2_url:
            PropertyType.objects.filter(pk=instance.pk).update(image_url=r2_url)


@receiver(pre_save, sender=RoomCategory)
def expire_discount_if_ended(sender, instance, **kwargs):
    """Automatically set has_discount to False when discount end date has passed"""
    if instance.pk:
        try:
            old_instance = RoomCategory.objects.get(pk=instance.pk)
            today = timezone.now().date()
            # If the discount was active but end date has passed, disable it
            if (old_instance.has_discount and 
                instance.discount_end_date and 
                instance.discount_end_date < today):
                instance.has_discount = False
        except RoomCategory.DoesNotExist:
            pass
