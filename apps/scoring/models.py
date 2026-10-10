"""Models for scoring (CAP-005)."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Evaluacion(models.Model):
    """Individual criterion evaluation for an application."""

    class Criterio(models.TextChoices):
        """Evaluation criteria groups."""

        SOCIOECONOMICO = "socioeconomico", _("Socioeconómico")
        ACADEMICO = "academico", _("Académico")
        EXCELENCIA = "excelencia", _("Excelencia")

    # Relations
    solicitud = models.ForeignKey(
        "applications.Solicitud",
        on_delete=models.CASCADE,
        related_name="evaluaciones",
        verbose_name=_("solicitud"),
    )
    criterio = models.CharField(
        _("criterio"),
        max_length=30,
        choices=Criterio.choices,
    )
    criterio_nombre = models.CharField(
        _("nombre del criterio"),
        max_length=200,
    )

    # Score
    puntaje = models.DecimalField(
        _("puntaje"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    observaciones = models.TextField(
        _("observaciones"),
        blank=True,
    )

    # Audit
    evaluado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="evaluaciones_realizadas",
        verbose_name=_("evaluado por"),
    )
    created_at = models.DateTimeField(
        _("fecha de creación"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        _("fecha de actualización"),
        auto_now=True,
    )

    class Meta:
        verbose_name = _("evaluación")
        verbose_name_plural = _("evaluaciones")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["solicitud", "criterio"],
                name="unique_evaluacion_per_criterio",
            ),
        ]

    def __str__(self):
        return f"{self.criterio_nombre} - {self.solicitud.radicado} - {self.puntaje}"


class PuntajeTotal(models.Model):
    """Total score and ranking for an application."""

    # Relations
    solicitud = models.OneToOneField(
        "applications.Solicitud",
        on_delete=models.CASCADE,
        related_name="puntaje_total",
        verbose_name=_("solicitud"),
    )

    # Scores
    puntaje_socioeconomico = models.DecimalField(
        _("puntaje socioeconómico"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    puntaje_academico = models.DecimalField(
        _("puntaje académico"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    puntaje_excelencia = models.DecimalField(
        _("puntaje excelencia"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    puntaje_total = models.DecimalField(
        _("puntaje total"),
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )

    # Rankings
    ranking_municipio = models.PositiveIntegerField(
        _("ranking por municipio"),
        null=True,
        blank=True,
    )
    ranking_general = models.PositiveIntegerField(
        _("ranking general"),
        null=True,
        blank=True,
    )

    # Additional
    observaciones = models.TextField(
        _("observaciones"),
        blank=True,
    )

    # Audit
    calculado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="puntajes_calculados",
        verbose_name=_("calculado por"),
    )
    fecha_calculo = models.DateTimeField(
        _("fecha de cálculo"),
        auto_now_add=True,
    )
    created_at = models.DateTimeField(
        _("fecha de creación"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        _("fecha de actualización"),
        auto_now=True,
    )

    class Meta:
        verbose_name = _("puntaje total")
        verbose_name_plural = _("puntajes totales")
        ordering = ["ranking_general"]

    def __str__(self):
        return f"{self.solicitud.radicado} - Total: {self.puntaje_total} - Ranking: {self.ranking_general}"
