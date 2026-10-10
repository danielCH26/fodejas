"""Add ACTO_ADMINISTRATIVO document type (CHG-303, CAP-010).

Required as the 4th normative attachment sent with each treasury
order (pagaré + carta de instrucciones + contrato + acto
administrativo / resolución de otorgamiento).

Tracked in: openspec/changes/chg-303-disbursement/tasks.md §Batch notes.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("legalization", "0002_add_changes_field"),
    ]

    operations = [
        migrations.AlterField(
            model_name="legaldocument",
            name="document_type",
            field=models.CharField(
                choices=[
                    ("PAGARE", "Pagaré"),
                    ("CARTA_INSTRUCCIONES", "Carta de Instrucciones"),
                    ("CONTRATO", "Contrato"),
                    ("ACTO_ADMINISTRATIVO", "Acto Administrativo"),
                ],
                max_length=30,
            ),
        ),
    ]
