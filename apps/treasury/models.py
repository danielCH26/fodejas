"""Models for treasury app - disbursement management."""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class DisbursementAuthorization(models.Model):
    """Authorization for beneficiary disbursement."""

    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", _("Pendiente")
        AUTORIZADO = "AUTORIZADO", _("Autorizado")
        ORDENADO = "ORDENADO", _("Ordenado a Tesorería")
        RECIBIDO = "RECIBIDO", _("Recibido por Tesorería")
        PAGADO = "PAGADO", _("Pagado")
        RECHAZADO = "RECHAZADO", _("Rechazado")
        VENCIDO = "VENCIDO", _("Vencido (5 días hábiles)")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legalization_process = models.ForeignKey(
        "legalization.LegalizationProcess",
        on_delete=models.CASCADE,
        related_name="disbursements",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDIENTE,
    )
    # Authorization signatures
    authorized_by_president = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authorized_disbursements_president",
    )
    authorized_by_secretary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="authorized_disbursements_secretary",
    )
    authorized_at = models.DateTimeField(null=True, blank=True)
    # Treasury order
    treasury_order_number = models.CharField(max_length=50, blank=True, default="")
    treasury_order_date = models.DateField(null=True, blank=True)
    # CHG-802: receipt timestamp set by `TreasuryService.mark_as_received`.
    # Sweep task `tesoreria_sweep_v5d` transitions to VENCIDO when
    # treasury_order_date is older than 5 working days without a
    # payment confirmation.
    treasury_received_at = models.DateTimeField(null=True, blank=True)
    # CHG-802: dedupe marker so re-running the alert task does not
    # double-notify on the same calendar day.
    last_alerted_at = models.DateTimeField(null=True, blank=True)
    # CHG-303: normative attachments sent to Tesorería. Each entry:
    # {document_type, document_id, post_sign_hash}. All 4 required
    # (PAGARE, CARTA_INSTRUCCIONES, CONTRATO, ACTO_ADMINISTRATIVO)
    # before status can transition to ORDENADO.
    # DB-level: nullable (null=True) because SQLite does not apply
    # callable defaults at INSERT time; the model-level default=list
    # provides an empty list when accessed in Python.
    treasury_order_attachments = models.JSONField(
        null=True,
        blank=True,
        default=list,
    )
    # Payment confirmation
    paid_at = models.DateTimeField(null=True, blank=True)
    payment_proof = models.FileField(
        upload_to="treasury/payment_proofs/",
        null=True,
        blank=True,
    )
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Disbursement {self.amount} - {self.status}"

    @property
    def is_fully_authorized(self):
        """Check if both authorities have authorized."""
        return bool(self.authorized_by_president and self.authorized_by_secretary)
