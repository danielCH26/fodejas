"""Migration: add fecha_firma to ActoAdministrativo (CHG-208)."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("governance", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="actoadministrativo",
            name="fecha_firma",
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name="fecha de firma",
            ),
        ),
    ]
