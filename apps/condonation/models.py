"""Models for termination causes and sanctions."""

import uuid

from django.conf import settings
from django.db import models


class TerminationRequest(models.Model):
    """Termination of scholarship agreement per Art. 14-15 Decreto 0372/2025."""

    class Cause(models.TextChoices):
        ABANDONO = "ABANDONO", "Abandono injustificado"
        RETIRO_VOLUNTARIO = "RETIRO_VOLUNTARIO", "Retiro voluntario"
        FINALIZACION = "FINALIZACION", "Finalización de periodos financiados"
        INFORMACION_FALSA = "INFORMACION_FALSA", "Adulteración o información falsa"
        SANCION_DISCIPLINARIA = "SANCION_DISCIPLINARIA", "Sanción disciplinaria/académica"
        PROMEDIO_BAJO = "PROMEDIO_BAJO", "Promedio < 3.5 acumulado"
        MUERTE = "MUERTE", "Muerte"
        # Art. 15 - disbursement termination only
        SUSPENSION_2_SEMESTRES = "SUSPENSION_2_SEMESTRES", "2 semestres consecutivos suspension"
        NO_RENOVACION = "NO_RENOVACION", "No renovación > 2 períodos"
        PROMEDIO_BAJO_2_PERIODOS = "PROMEDIO_BAJO_2_PERIODOS", "Promedio bajo > 2 períodos"

    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_SESION = "EN_SESION", "En revisión"
        TERMINADO = "TERMINADO", "Terminado"
        RECHAZADO = "RECHAZADO", "Rechazado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legalization_process = models.ForeignKey(
        "legalization.LegalizationProcess",
        on_delete=models.CASCADE,
        related_name="termination_requests",
    )
    cause = models.CharField(max_length=30, choices=Cause.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDIENTE,
    )
    description = models.TextField(blank=True, default="")
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="termination_requests",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="terminations_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Termination {self.cause} - {self.status}"


class Sanction(models.Model):
    """Sanction for reimbursement per Art. 17 Decreto 0372/2025."""

    class Justification(models.TextChoices):
        ENFERMEDAD_GRAVE = "ENFERMEDAD_GRAVE", "Enfermedad grave certificada"
        ACCIDENTE = "ACCIDENTE", "Accidente con afectación significativa"
        EMERGENCIA_FAMILIAR = "EMERGENCIA_FAMILIAR", "Emergencia familiar"
        TRASLADO_EXTERIOR = "TRASLADO_EXTERIOR", "Traslado definitivo fuera del país"

    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        EN_REVISION = "EN_REVISION", "En revisión"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"
        PAGADA = "PAGADA", "Pagada"
        CONDONADA = "CONDONADA", "Condonada"
        VENCIDO = "VENCIDO", "Vencido (30 días calendario)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    termination = models.OneToOneField(
        TerminationRequest,
        on_delete=models.CASCADE,
        related_name="sanction",
    )
    base_amount = models.DecimalField(max_digits=12, decimal_places=2)
    ipc_adjustment = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="IPC adjustment added to base amount",
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDIENTE,
    )
    justification = models.CharField(
        max_length=30,
        choices=Justification.choices,
        null=True,
        blank=True,
    )
    justification_details = models.TextField(blank=True, default="")
    justification_approved = models.BooleanField(default=False)
    payment_proof = models.FileField(
        upload_to="condonation/payments/",
        null=True,
        blank=True,
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    # CHG-802: deadline for the 30-calendar-day exoneration window
    # (Decreto 0372/2025 Art. 17). Populated by
    # ``SanctionService.submit_justification`` when the sanction
    # transitions to ``EN_REVISION``.
    fecha_limite = models.DateTimeField(null=True, blank=True)
    # CHG-802: dedupe marker for the preventive alert task.
    last_alerted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sanctions_reviewed",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Sanction ${self.total_amount} - {self.status}"

    def calculate_total(self):
        """Calculate total = base + IPC adjustment."""
        return self.base_amount + self.ipc_adjustment
