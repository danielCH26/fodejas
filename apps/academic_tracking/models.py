"""Models for academic tracking."""

import uuid

from django.db import models


class AcademicRecord(models.Model):
    """Academic record for a legalized beneficiary."""

    class Status(models.TextChoices):
        ACTIVO = "ACTIVO", "Activo"
        ACADEMICO_BAJO = "ACADEMICO_BAJO", "Bajo Rendimiento"
        SUSPENDIDO = "SUSPENDIDO", "Suspendido"
        GRADUADO = "GRADUADO", "Graduado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    legalization_process = models.OneToOneField(
        "legalization.LegalizationProcess",
        on_delete=models.CASCADE,
        related_name="academic_record",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVO,
    )
    cumulative_average = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        help_text="Cumulative weighted average",
    )
    semester_count = models.PositiveIntegerField(default=0)
    consecutive_low_semesters = models.PositiveIntegerField(
        default=0,
        help_text="Consecutive semesters below 3.5",
    )
    last_reviewed_at = models.DateTimeField(null=True, blank=True)
    # CHG-506: retorno al Archipiélago
    retorno_archipelago = models.BooleanField(
        null=True,
        blank=True,
        help_text="True=retornó al Archipiélago, False=no retornó, null=sin anotar",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return f"Academic Record {self.legalization_process} - {self.cumulative_average}"


class GradeEntry(models.Model):
    """Grade entry for a single course in a semester."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    academic_record = models.ForeignKey(
        AcademicRecord,
        on_delete=models.CASCADE,
        related_name="grades",
    )
    semester = models.PositiveIntegerField(
        help_text="Semester number (1, 2, 3, ...)",
    )
    course_name = models.CharField(max_length=200)
    credits = models.PositiveIntegerField()
    grade = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        help_text="Grade 0-5",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["semester", "course_name"]
        unique_together = ["academic_record", "semester", "course_name"]

    def __str__(self):
        return f"{self.course_name}: {self.grade} ({self.semester})"


class AcademicAlert(models.Model):
    """Alert for academic performance issues."""

    class AlertType(models.TextChoices):
        BAJO_RENDIMIENTO = "BAJO_RENDIMIENTO", "Bajo Rendimiento"
        PROBACION = "PROBACION", "Probación Académica"
        SUSPENSION = "SUSPENSION", "Suspensión Automática"
        GRADUACION = "GRADUACION", "Graduación"

    class Status(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        REVISADA = "REVISADA", "Revisada"
        RESUELTA = "RESUELTA", "Resuelta"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    academic_record = models.ForeignKey(
        AcademicRecord,
        on_delete=models.CASCADE,
        related_name="alerts",
    )
    alert_type = models.CharField(max_length=30, choices=AlertType.choices)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDIENTE,
    )
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Alert {self.alert_type} - {self.status}"
