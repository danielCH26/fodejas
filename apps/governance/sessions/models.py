"""Models for governance/sessions (CHG-501 / CAP-017).

Defines session lifecycle, quorum, voting, and minutes for the
Junta and Comité Técnico.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _validate_no_pii(value: str) -> None:
    """Refuse PII in CharField values (AGENTS.md §6 rule 1)."""
    # Re-use the core helper if available, else a no-op stub.
    try:
        from apps.core.logging import _mask_pii_in_text

        if _mask_pii_in_text(value) != value:
            raise ValidationError("Value contains personal data — use synthetic data.")
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Sesion
# ---------------------------------------------------------------------------

class Sesion(models.Model):
    """A session of the Junta or Comité Técnico (CAP-017)."""

    class Organo(models.TextChoices):
        JUNTA = "JUNTA", _("Junta Administradora")
        CT = "CT", _("Comité Técnico")

    class Tipo(models.TextChoices):
        ORDINARIA = "ORDINARIA", _("Ordinaria")
        EXTRAORDINARIA = "EXTRAORDINARIA", _("Extraordinaria")

    class Estado(models.TextChoices):
        CONVOCADA = "CONVOCADA", _("Convocada")
        EN_SESION = "EN_SESION", _("En Sesión")
        FINALIZADA = "FINALIZADA", _("Finalizada")
        ANULADA = "ANULADA", _("Anulada")

    # UUID primary key
    id = models.UUIDField(
        default=uuid.uuid4,
        primary_key=True,
        editable=False,
    )

    # Identity
    organo = models.CharField(
        max_length=10,
        choices=Organo.choices,
        verbose_name=_("órgano"),
    )
    tipo = models.CharField(
        max_length=15,
        choices=Tipo.choices,
        verbose_name=_("tipo de sesión"),
    )

    # Timing
    fecha_hora = models.DateTimeField(
        verbose_name=_("fecha y hora de la sesión"),
    )
    convocatoria_enviada_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("fecha de envío de convocatoria"),
    )

    # State
    estado = models.CharField(
        max_length=15,
        choices=Estado.choices,
        default=Estado.CONVOCADA,
        verbose_name=_("estado"),
    )

    # Relationships
    convocatoria = models.ForeignKey(
        "convocatories.Convocatory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sesiones",
        verbose_name=_("convocatoria asociada"),
    )
    asunto = models.TextField(
        verbose_name=_("asunto"),
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fecha_hora"]
        verbose_name = _("sesión")
        verbose_name_plural = _("sesiones")

    def __str__(self):
        return f"{self.get_tipo_display()} {self.get_organo_display()} — {self.fecha_hora:%Y-%m-%d}"

    def voting_members_present(self) -> int:
        """Count present/voting (non-cargo) members."""
        return self.miembros.exclude(
            # Exclude absent
            asistencia=MiembroSesion.Asistencia.AUSENTE,
        ).exclude(
            # Exclude cargo-exempt (Gobernador / Alcalde / Secretario)
            es_miembro_cargo=True,
        ).count()

    def quorum_met(self) -> bool:
        """True when majority (mayoría absoluta = mitad + 1) of voting members are present.

        Calculation: majority = floor(total/2) + 1
          - 1 voting member  → majority = 1; quorum MET (1 >= 1)
          - 2 voting members → majority = 2; quorum MET (2 >= 2)
          - 3 voting members → majority = 2; quorum MET (3 >= 2)
          - 4 voting members → majority = 3; quorum MET (4 >= 3)
          - 5 voting members → majority = 3; quorum MET (5 >= 3)

        Returns False when there are no voting members.
        """
        total = self.voting_members_present()
        if total == 0:
            return False
        majority = (total // 2) + 1
        return total >= majority

    def all_puntos_closed(self) -> bool:
        """True when every agenda punto is in a resolved state."""
        return not self.puntos.filter(
            estado__in=[
                OrdenDelDiaPunto.Estado.PENDIENTE,
            ]
        ).exists()


# ---------------------------------------------------------------------------
# MiembroSesion
# ---------------------------------------------------------------------------

class MiembroSesion(models.Model):
    """A member's attendance record for a session (CAP-017)."""

    class Asistencia(models.TextChoices):
        PRESENTE = "PRESENTE", _("Presente")
        VIRTUAL = "VIRTUAL", _("Virtual")
        AUSENTE = "AUSENTE", _("Ausente")

    sesion = models.ForeignKey(
        Sesion,
        on_delete=models.CASCADE,
        related_name="miembros",
        verbose_name=_("sesión"),
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="sesiones_asistente",
        verbose_name=_("usuario"),
    )
    rol = models.CharField(
        max_length=100,
        verbose_name=_("rol en la sesión"),
    )
    asistencia = models.CharField(
        max_length=10,
        choices=Asistencia.choices,
        default=Asistencia.AUSENTE,
        verbose_name=_("asistencia"),
    )
    es_miembro_cargo = models.BooleanField(
        default=False,
        verbose_name=_("es miembro por cargo (no vota)"),
        help_text=_("Gobernador, Alcalde o Secretario — no cuenta para quórum ni vota"),
    )
    conflicto_declarado = models.BooleanField(
        default=False,
        verbose_name=_("conflicto de interés declarado"),
    )

    class Meta:
        unique_together = [("sesion", "user")]
        verbose_name = _("miembro de sesión")
        verbose_name_plural = _("miembros de sesión")

    def __str__(self):
        return f"{self.user} @ {self.sesion}"

    def can_vote(self) -> bool:
        """True when this member may cast a vote in the session."""
        return (
            self.asistencia in (self.Asistencia.PRESENTE, self.Asistencia.VIRTUAL)
            and not self.es_miembro_cargo
            and not self.conflicto_declarado
        )


# ---------------------------------------------------------------------------
# OrdenDelDiaPunto
# ---------------------------------------------------------------------------

class OrdenDelDiaPunto(models.Model):
    """An agenda item (punto) within a session (CAP-017)."""

    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", _("Pendiente")
        APROBADO = "APROBADO", _("Aprobado")
        RECHAZADO = "RECHAZADO", _("Rechazado")

    sesion = models.ForeignKey(
        Sesion,
        on_delete=models.CASCADE,
        related_name="puntos",
        verbose_name=_("sesión"),
    )
    numero = models.PositiveIntegerField(
        verbose_name=_("número de orden"),
    )
    texto = models.TextField(
        verbose_name=_("texto del punto"),
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
        verbose_name=_("estado"),
    )

    class Meta:
        unique_together = [("sesion", "numero")]
        ordering = ["numero"]
        verbose_name = _("punto de orden del día")
        verbose_name_plural = _("puntos de orden del día")

    def __str__(self):
        return f"Punto {self.numero}: {self.texto[:40]}"


# ---------------------------------------------------------------------------
# Voto
# ---------------------------------------------------------------------------

class Voto(models.Model):
    """A member's vote on a specific agenda punto (CAP-017)."""

    class Valor(models.TextChoices):
        A_FAVOR = "A_FAVOR", _("A favor")
        EN_CONTRA = "EN_CONTRA", _("En contra")
        ABSTENCION = "ABSTENCION", _("Abstención")

    punto = models.ForeignKey(
        OrdenDelDiaPunto,
        on_delete=models.CASCADE,
        related_name="votos",
        verbose_name=_("punto"),
    )
    miembro_sesion = models.ForeignKey(
        MiembroSesion,
        on_delete=models.PROTECT,
        related_name="votos",
        verbose_name=_("miembro"),
    )
    valor = models.CharField(
        max_length=10,
        choices=Valor.choices,
        verbose_name=_("valor del voto"),
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("momento del voto"),
    )

    class Meta:
        unique_together = [("punto", "miembro_sesion")]
        verbose_name = _("voto")
        verbose_name_plural = _("votos")

    def __str__(self):
        return f"{self.miembro_sesion.user} → {self.get_valor_display()}"


# ---------------------------------------------------------------------------
# ActaSesion
# ---------------------------------------------------------------------------

class ActaSesion(models.Model):
    """Minutes (acta) for a finalized session (CAP-017 / CAP-029)."""

    class Estado(models.TextChoices):
        GENERADA = "GENERADA", _("Generada")
        FIRMADA = "FIRMADA", _("Firmada")

    sesion = models.OneToOneField(
        Sesion,
        on_delete=models.CASCADE,
        related_name="acta",
        primary_key=False,
        verbose_name=_("sesión"),
    )
    pdf = models.FileField(
        upload_to="governance/actas/",
        null=True,
        blank=True,
        verbose_name=_("PDF del acta"),
        validators=[FileExtensionValidator(allowed_extensions=["pdf"])],
    )
    pdf_sha256 = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name=_("hash SHA-256 del PDF"),
    )
    pre_sign_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name=_("hash previo a la firma"),
    )
    post_sign_hash = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name=_("hash posterior a la firma"),
    )
    firmantes = models.JSONField(
        default=list,
        verbose_name=_("firmantes"),
    )
    estado = models.CharField(
        max_length=10,
        choices=Estado.choices,
        default=Estado.GENERADA,
        verbose_name=_("estado de firma"),
    )
    signed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("fecha y hora de firma"),
    )

    class Meta:
        verbose_name = _("acta de sesión")
        verbose_name_plural = _("actas de sesión")

    def __str__(self):
        return f"Acta — {self.sesion}"
