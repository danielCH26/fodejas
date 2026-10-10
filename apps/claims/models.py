"""Models for claims (CHG-205)."""

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Reclamacion(models.Model):
    """Reclamación en 1ª instancia ante la Junta Directiva."""

    class TipoReclamacion(models.TextChoices):
        PUNTAJE = "puntaje", _("Puntaje incorrecto")
        REQUISITO = "requisito", _("Requisito mal validado")
        OTRO = "otro", _("Otro")

    class Estado(models.TextChoices):
        PRESENTADA = "presentada", _("Presentada")
        EN_REVISION = "en_revision", _("En revisión")
        RESUELTA = "resuelta", _("Resuelta")
        RECHAZADA = "rechazada", _("Rechazada")

    # UUID para URLs públicas
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    # Relación con la postulación
    solicitud = models.ForeignKey(
        "applications.Solicitud",
        on_delete=models.CASCADE,
        related_name="reclamaciones",
        verbose_name=_("solicitud"),
    )

    # Datos de la reclamación
    tipo = models.CharField(
        max_length=20,
        choices=TipoReclamacion.choices,
        verbose_name=_("tipo de reclamación"),
    )
    descripcion = models.TextField(
        verbose_name=_("descripción"),
        help_text=_("Motivo de la reclamación"),
    )
    evidencia = models.FileField(
        upload_to="reclamaciones/%Y/%m/",
        blank=True,
        null=True,
        verbose_name=_("evidencia"),
    )

    # Estado y resolución
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PRESENTADA,
        verbose_name=_("estado"),
    )
    respuesta = models.TextField(
        blank=True,
        verbose_name=_("respuesta"),
        help_text=_("Fundamentación de la resolución"),
    )
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reclamaciones_resueltas",
        verbose_name=_("resuelto por"),
    )
    fecha_resolucion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("fecha de resolución"),
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Reclamación")
        verbose_name_plural = _("Reclamaciones")

    def __str__(self):
        return f"Reclamación {self.uuid} - {self.solicitud.radicado}"


class ReclamacionHistorial(models.Model):
    """Historial de cambios de estado de una reclamación."""

    reclamacion = models.ForeignKey(
        Reclamacion,
        on_delete=models.CASCADE,
        related_name="historial",
        verbose_name=_("reclamación"),
    )
    estado_anterior = models.CharField(
        max_length=20,
        verbose_name=_("estado anterior"),
    )
    estado_nuevo = models.CharField(
        max_length=20,
        verbose_name=_("estado nuevo"),
    )
    observacion = models.TextField(
        blank=True,
        verbose_name=_("observación"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("actor"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Historial de reclamación")
        verbose_name_plural = _("Historial de reclamaciones")

    def __str__(self):
        return f"{self.reclamacion.uuid}: {self.estado_anterior} → {self.estado_nuevo}"


class Apelacion(models.Model):
    """Apelación en 2ª instancia ante la Oficina Jurídica."""

    class Estado(models.TextChoices):
        PRESENTADA = "presentada", _("Presentada")
        EN_ANALISIS = "en_analisis", _("En análisis")
        CONFIRMADA = "confirmada", _("Confirmada")
        REVOCADA = "revocada", _("Revocada")

    # UUID para URLs públicas
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    # Reclamación de 1ª instancia (obligatoria)
    reclamacion = models.ForeignKey(
        Reclamacion,
        on_delete=models.CASCADE,
        related_name="apelaciones",
        verbose_name=_("reclamación"),
        help_text=_("Reclamación de primera instancia objeto de apelación"),
    )

    # Datos de la apelación
    descripcion = models.TextField(
        verbose_name=_("descripción"),
        help_text=_("Fundamentos de la apelación"),
    )
    evidencia = models.FileField(
        upload_to="apelaciones/%Y/%m/",
        blank=True,
        null=True,
        verbose_name=_("evidencia"),
    )

    # Estado y resolución
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.PRESENTADA,
        verbose_name=_("estado"),
    )
    respuesta = models.TextField(
        blank=True,
        verbose_name=_("respuesta"),
        help_text=_("Fundamentación de la resolución"),
    )
    resuelto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="apelaciones_resueltas",
        verbose_name=_("resuelto por"),
    )
    fecha_resolucion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("fecha de resolución"),
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("Apelación")
        verbose_name_plural = _("Apelaciones")

    def __str__(self):
        return f"Apelación {self.uuid} - Reclamación {self.reclamacion.uuid}"

    def clean(self):
        from django.core.exceptions import ValidationError

        # Validar que la reclamación esté en estado terminal
        if self.reclamacion.estado not in [
            Reclamacion.Estado.RESUELTA,
            Reclamacion.Estado.RECHAZADA,
        ]:
            raise ValidationError(_("Solo se puede apelar una reclamación resuelta o rechazada."))


class ApelacionHistorial(models.Model):
    """Historial de cambios de estado de una apelación."""

    apelacion = models.ForeignKey(
        Apelacion,
        on_delete=models.CASCADE,
        related_name="historial",
        verbose_name=_("apelación"),
    )
    estado_anterior = models.CharField(
        max_length=20,
        verbose_name=_("estado anterior"),
    )
    estado_nuevo = models.CharField(
        max_length=20,
        verbose_name=_("estado nuevo"),
    )
    observacion = models.TextField(
        blank=True,
        verbose_name=_("observación"),
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        verbose_name=_("actor"),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = _("Historial de apelación")
        verbose_name_plural = _("Historial de apelaciones")

    def __str__(self):
        return f"{self.apelacion.uuid}: {self.estado_anterior} → {self.estado_nuevo}"
