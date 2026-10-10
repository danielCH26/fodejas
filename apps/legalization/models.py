"""Models for legal document management."""

import uuid

from django.conf import settings
from django.db import models


class LegalizationProcess(models.Model):
    """Tracks the overall legalization process for a beneficiary."""

    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_PROCESO = "EN_PROCESO", "En Proceso"
        LEGALIZADO = "LEGALIZADO", "Legalizado"
        CANCELADO = "CANCELADO", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    beneficiary = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="legalization_processes",
    )
    convocatoria = models.ForeignKey(
        "convocatories.Convocatory",
        on_delete=models.CASCADE,
        related_name="legalization_processes",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDIENTE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ["beneficiary", "convocatoria"]

    def __str__(self):
        return f"Legalization {self.beneficiary} - {self.status}"


class LegalDocument(models.Model):
    """Legal document (promissory note, instructions, contract)."""

    class DocumentType(models.TextChoices):
        PAGARE = "PAGARE", "Pagaré"
        CARTA_INSTRUCCIONES = "CARTA_INSTRUCCIONES", "Carta de Instrucciones"
        CONTRATO = "CONTRATO", "Contrato"
        # CHG-303: Acto administrativo (resolución/acta de otorgamiento).
        # The 4th normative attachment sent with each treasury order.
        ACTO_ADMINISTRATIVO = "ACTO_ADMINISTRATIVO", "Acto Administrativo"

    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        FIRMADO = "FIRMADO", "Firmado"
        LEGALIZADO = "LEGALIZADO", "Legalizado"
        CANCELADO = "CANCELADO", "Cancelado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    process = models.ForeignKey(
        LegalizationProcess,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.CharField(max_length=30, choices=DocumentType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDIENTE,
    )
    pre_sign_hash = models.CharField(max_length=64, blank=True, default="")
    post_sign_hash = models.CharField(max_length=64, blank=True, default="")
    pdf = models.FileField(upload_to="legalization/pdfs/", null=True, blank=True)
    signed_at = models.DateTimeField(null=True, blank=True)
    # CHG-301: stores the full signature metadata JSON so the
    # SignatureResult can be reconstructed without re-running the signer
    # (idempotency path).
    changes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["process", "document_type"]
        ordering = ["document_type"]

    def __str__(self):
        return f"{self.document_type} - {self.status}"
