# Generated manually to fix orphaned table issue

from django.db import migrations, connection


class Migration(migrations.Migration):

    dependencies = [
        ("payments", "0003_fix_published_date_field"),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS payments_invoicereservation;",
            reverse_sql=migrations.RunSQL.noop
        ),
    ]
