"""Add treasury_order_attachments JSONField (CHG-303, CAP-010).

Tracks the 4 normative documents sent with each treasury order:
  1. PAGARE
  2. CARTA_INSTRUCCIONES
  3. CONTRATO
  4. ACTO_ADMINISTRATIVO

Each entry stores the LegalDocument UUID and the post-sign SHA-256
hash as evidence of integrity at the time the order was dispatched.

Batch B (views) populates the ACTO_ADMINISTRATIVO attachment via
the authorize-action form.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("treasury", "0002_add_treasury_received_at_and_vencido"),
    ]

    operations = [
        migrations.AddField(
            model_name="disbursementauthorization",
            name="treasury_order_attachments",
            field=models.JSONField(
                null=True,
                blank=True,
                default=None,
                help_text=(
                    "JSON list of normative attachments sent to Tesorería. "
                    "Each entry: {document_type, document_id, post_sign_hash}. "
                    "Must contain all 4 types before status transitions to ORDENADO."
                ),
            ),
        ),
    ]
