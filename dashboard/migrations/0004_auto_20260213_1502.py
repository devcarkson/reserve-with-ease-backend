from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0003_add_reservation_change_percentage'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlatformVisit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('visit_date', models.DateField()),
                ('page_views', models.IntegerField(default=0)),
                ('unique_visitors', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-visit_date'],
            },
        ),
        migrations.CreateModel(
            name='PlatformVisitLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(max_length=255)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('referrer', models.TextField(blank=True)),
                ('path', models.CharField(max_length=500, blank=True)),
                ('is_unique', models.BooleanField(default=True)),
                ('visited_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-visited_at'],
            },
        ),
    ]
