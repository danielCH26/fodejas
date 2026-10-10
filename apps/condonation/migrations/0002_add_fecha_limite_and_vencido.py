"""Add ``fecha_limite``, ``last_alerted_at`` and VENCIDO state to Sanction (CHG-802).

Adds the deadline-tracking fields required by the new Celery
sweep tasks (``exoneracion_sweep_v30d`` and
``exoneracion_alert_v30d``) and extends the ``Status`` enum with
``VENCIDO`` (set by the sweep when the 30-calendar-day window has
elapsed without a justification decision).
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("condonation", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sanction",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("EN_REVISION", "En revisión"),
                    ("APROBADA", "Aprobada"),
                    ("RECHAZADA", "Rechazada"),
                    ("PAGADA", "Pagada"),
                    ("CONDONADA", "Condonada"),
                    ("VENCIDO", "Vencido (30 días calendario)"),
                ],
                default="PENDIENTE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="sanction",
            name="fecha_limite",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="sanction",
            name="last_alerted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
