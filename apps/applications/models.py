"""Models for applications (FUI)."""
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class Solicitud(models.Model):
    """Application/FUI model for convocation applications."""

    class Estado(models.TextChoices):
        """Application states."""

        BORRADOR = "borrador", _("Borrador")
        COMPLETA = "completa", _("Completa")
        RADICADA = "radicada", _("Radicada")
        EN_VERIFICACION = "en_verificacion", _("En Verificación")
        VERIFICADA = "verificada", _("Verificada")
        RECHAZADA = "rechazada", _("Rechazada")

    # UUID for obfuscated URLs
    uuid = models.UUIDField(
        _("UUID"),
        default=uuid.uuid4,
        unique=True,
        db_index=True,
        editable=False,
    )

    # Radicado: FODEJAS-YYYY-NNNNN
    radicado = models.CharField(
        _("radicado"),
        max_length=20,
        unique=True,
        null=True,
        blank=True,
    )

    # Relations
    convocatoria = models.ForeignKey(
        "convocatories.Convocatory",
        on_delete=models.PROTECT,
        related_name="solicitudes",
        verbose_name=_("convocatoria"),
    )
    aspirante = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitudes",
        verbose_name=_("aspirante"),
    )

    # State
    estado = models.CharField(
        _("estado"),
        max_length=20,
        choices=Estado.choices,
        default=Estado.BORRADOR,
    )

    # Data fields (JSON)
    datos_personales = models.JSONField(
        _("datos personales"),
        default=dict,
        blank=True,
    )
    datos_academicos = models.JSONField(
        _("datos académicos"),
        default=dict,
        blank=True,
    )
    datos_socioeconomicos = models.JSONField(
        _("datos socioeconómicos"),
        default=dict,
        blank=True,
    )

    # Consentimiento (CHG-105)
    consentimiento = models.BooleanField(
        _("consentimiento tratamiento de datos"),
        default=False,
    )
    consentimiento_fecha = models.DateTimeField(
        _("fecha de consentimiento"),
        null=True,
        blank=True,
    )

    # PDF
    pdf_generado = models.FileField(
        _("PDF generado"),
        upload_to="solicitudes/pdf/%Y/%m/",
        null=True,
        blank=True,
    )
    pdf_sha256 = models.CharField(
        _("hash SHA-256 del PDF"),
        max_length=64,
        null=True,
        blank=True,
    )

    # Wizard state
    current_step = models.PositiveIntegerField(
        _("paso actual del wizard"),
        default=1,
    )

    # Timestamps
    created_at = models.DateTimeField(
        _("fecha de creación"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        _("fecha de actualización"),
        auto_now=True,
    )

    class Meta:
        verbose_name = _("solicitud")
        verbose_name_plural = _("solicitudes")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["convocatoria", "aspirante"],
                name="unique_solicitud_per_convocatoria",
            ),
        ]

    def __str__(self):
        return self.radicado or f"Solicitud {self.id} - {self.aspirante.email}"

    def puede_editar(self):
        """Check if application can still be edited."""
        return self.estado in {self.Estado.BORRADOR, self.Estado.COMPLETA}


class Anexo(models.Model):
    """Attachment model for application documents."""

    class TipoAnxo(models.TextChoices):
        """Attachment types."""

        CEDULA = "cedula", _("Cédula de ciudadanía")
        CERTIFICADO_NOTAS = "certificado_notas", _("Certificado de notas")
        DIPLOMA = "diploma", _("Diploma o certificación de grado")
        RECIBO_PAGO = "recibo_pago", _("Recibo de pago")
        OTRO = "otro", _("Otro documento")

    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name="anexos",
        verbose_name=_("solicitud"),
    )
    tipo_anexo = models.CharField(
        _("tipo de anexo"),
        max_length=30,
        choices=TipoAnxo.choices,
    )
    archivo = models.FileField(
        _("archivo"),
        upload_to="solicitudes/anexos/%Y/%m/%d/",
        help_text=_("Máximo 10MB, formatos PDF, JPG, PNG"),
    )
    nombre_original = models.CharField(
        _("nombre original"),
        max_length=255,
    )
    tamano = models.PositiveIntegerField(
        _("tamaño en bytes"),
    )
    mime_type = models.CharField(
        _("tipo MIME"),
        max_length=100,
    )
    sha256 = models.CharField(
        _("hash SHA-256"),
        max_length=64,
    )
    validado = models.BooleanField(
        _("validado"),
        default=False,
    )
    fecha_validacion = models.DateTimeField(
        _("fecha de validación"),
        null=True,
        blank=True,
    )
    observaciones = models.TextField(
        _("observaciones"),
        blank=True,
    )
    created_at = models.DateTimeField(
        _("fecha de creación"),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("anexo")
        verbose_name_plural = _("anexos")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.tipo_anexo} - {self.solicitud.radicado}"


class RequisitoValidacion(models.Model):
    """Validation of individual requirements for an application."""

    class Estado(models.TextChoices):
        """Validation states for each requirement."""
        PENDIENTE = "pendiente", _("Pendiente")
        VERIFICADO = "verificado", _("Verificado")
        RECHAZADO = "rechazado", _("Rechazado")
        SUBSANAR = "subsanar", _("Subsanar")

    # Relations
    solicitud = models.ForeignKey(
        Solicitud,
        on_delete=models.CASCADE,
        related_name="validaciones",
        verbose_name=_("solicitud"),
    )
    requisito_code = models.CharField(
        _("código del requisito"),
        max_length=50,
    )
    requisito_nombre = models.CharField(
        _("nombre del requisito"),
        max_length=200,
    )

    # Validation state
    estado = models.CharField(
        _("estado"),
        max_length=20,
        choices=Estado.choices,
        default=Estado.PENDIENTE,
    )

    # Evidence
    evidencia = models.FileField(
        _("evidencia"),
        upload_to="validaciones/evidencia/%Y/%m/",
        null=True,
        blank=True,
    )
    observaciones = models.TextField(
        _("observaciones"),
        blank=True,
    )

    # Audit
    validado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="validaciones_realizadas",
        verbose_name=_("validado por"),
    )
    fecha_validacion = models.DateTimeField(
        _("fecha de validación"),
        null=True,
        blank=True,
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
        verbose_name = _("validación de requisito")
        verbose_name_plural = _("validaciones de requisitos")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["solicitud", "requisito_code"],
                name="unique_validacion_per_requisito",
            ),
        ]

    def __str__(self):
        return f"{self.requisito_nombre} - {self.solicitud.radicado} - {self.get_estado_display()}"


class RadicadoSecuencial(models.Model):
    """Sequence counter for radicado generation."""

    anio = models.PositiveIntegerField(
        _("año"),
        unique=True,
    )
    secuencia = models.PositiveIntegerField(
        _("secuencia"),
        default=0,
    )

    class Meta:
        verbose_name = _("secuencial de radicado")
        verbose_name_plural = _("secuenciales de radicado")

    def __str__(self):
        return f"{self.anio}-{self.secuencia:05d}"
