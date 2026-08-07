"""Models for governance app (CHG-207)."""
import uuid
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class SecuencialActo(models.Model):
    """Secuencial para numeración de actos administrativos."""

    tipo = models.CharField(
        max_length=20,
        unique=True,
        verbose_name=_("tipo de acto"),
    )
    anio = models.PositiveIntegerField(
        verbose_name=_("año"),
    )
    secuencia = models.PositiveIntegerField(
        default=0,
        verbose_name=_("secuencia"),
    )

    class Meta:
        unique_together = ["tipo", "anio"]
        verbose_name = _("secuencial de acto")
        verbose_name_plural = _("secuenciales de actos")

    def __str__(self):
        return f"{self.tipo}-{self.anio}-{self.secuencia:05d}"


class ActoAdministrativo(models.Model):
    """Acto administrativo generado por la Junta."""

    class Tipo(models.TextChoices):
        RESOLUCION = "resolucion", _("Resolución")
        ACTA = "acta", _("Acta")
        MODIFICATORIO = "modificatorio", _("Acto Modificatorio")
        CERTIFICACION = "certificacion", _("Certificación")

    class Estado(models.TextChoices):
        BORRADOR = "borrador", _("Borrador")
        FIRMADO = "firmado", _("Firmado")
        PUBLICADO = "publicado", _("Publicado")
        ANULADO = "anulado", _("Anulado")

    # UUID
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )

    # Numeración
    numero = models.CharField(
        max_length=30,
        unique=True,
        verbose_name=_("número"),
    )
    tipo = models.CharField(
        max_length=20,
        choices=Tipo.choices,
        verbose_name=_("tipo de acto"),
    )

    # Fechas
    fecha_expedicion = models.DateField(
        verbose_name=_("fecha de expedición"),
    )
    fecha_publicacion = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("fecha de publicación"),
    )

    # Contenido
    asunto = models.TextField(
        verbose_name=_("asunto"),
    )
    considerandos = models.JSONField(
        default=list,
        verbose_name=_("considerandos"),
    )
    resolutivo = models.TextField(
        verbose_name=_("resolutivo"),
    )

    # Referencia para actos modificatorios
    acto_original = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="modificatorios",
        verbose_name=_("acto original"),
    )

    # Archivo
    pdf = models.FileField(
        upload_to="actos/%Y/%m/",
        null=True,
        blank=True,
        verbose_name=_("PDF"),
    )
    pdf_sha256 = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name=_("hash SHA-256 del PDF"),
    )

    # Estado
    estado = models.CharField(
        max_length=20,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        verbose_name=_("estado"),
    )

    # Firmantes
    firmantes = models.JSONField(
        default=list,
        verbose_name=_("firmantes"),
    )

    # Metadata
    convocatoria = models.ForeignKey(
        "convocatories.Convocatory",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="actos",
        verbose_name=_("convocatoria"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = _("acto administrativo")
        verbose_name_plural = _("actos administrativos")

    def __str__(self):
        return f"{self.numero} - {self.asunto[:50]}"


class ListadoDefinitivo(models.Model):
    """Listado definitivo de beneficiarios publicado."""

    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
        db_index=True,
    )
    convocatoria = models.OneToOneField(
        "convocatories.Convocatory",
        on_delete=models.CASCADE,
        related_name="listado_definitivo",
        verbose_name=_("convocatoria"),
    )

    # Ranking final (lista de IDs de solicitudes)
    ranking = models.JSONField(
        verbose_name=_("ranking"),
    )

    # Acto administrativo que aprueba el listado
    acto = models.ForeignKey(
        ActoAdministrativo,
        on_delete=models.PROTECT,
        related_name="listados",
        verbose_name=_("acto administrativo"),
    )

    # Fechas
    fecha_publicacion = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("fecha de publicación"),
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("listado definitivo")
        verbose_name_plural = _("listados definitivos")

    def __str__(self):
        return f"Listado {self.convocatoria.nombre}"
