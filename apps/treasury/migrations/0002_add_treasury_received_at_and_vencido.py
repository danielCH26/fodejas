"""Add treasury_received_at, last_alerted_at and VENCIDO/RECIBIDO states (CHG-802).

Adds the deadline-tracking fields required by the new Celery
sweep tasks (``tesoreria_sweep_v5d`` and ``tesoreria_alert_v5d``)
and extends the ``Status`` enum with ``RECIBIDO`` (set when
Tesorería acknowledges receipt of the order) and ``VENCIDO`` (set
by the sweep when the 5-working-day window has elapsed).
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("treasury", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="disbursementauthorization",
            name="status",
            field=models.CharField(
                choices=[
                    ("PENDIENTE", "Pendiente"),
                    ("AUTORIZADO", "Autorizado"),
                    ("ORDENADO", "Ordenado a Tesorería"),
                    ("RECIBIDO", "Recibido por Tesorería"),
                    ("PAGADO", "Pagado"),
                    ("RECHAZADO", "Rechazado"),
                    ("VENCIDO", "Vencido (5 días hábiles)"),
                ],
                default="PENDIENTE",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="disbursementauthorization",
            name="treasury_received_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="disbursementauthorization",
            name="last_alerted_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
