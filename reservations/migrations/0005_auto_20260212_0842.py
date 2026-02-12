from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reservations', '0004_reservation_room_category_alter_reservation_room'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='original_price',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name='reservation',
            name='discount_percentage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
    ]
