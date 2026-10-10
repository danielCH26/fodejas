"""Models for convocatories app (stub for now)."""
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import ModalidadApoyo, MunicipioIsla, NivelFormacion


class ActivasManager(models.Manager):
    """Manager that filters convocatorias in ejecutable estados."""

    def get_queryset(self):
        qs = super().get_queryset()
        # Use string values to avoid forward reference issues
        ejecutable_estados = [
            "publicada",
            "en_inscripcion",
            "en_verificacion",
            "en_calificacion",
            "definitiva",
        ]
        return qs.filter(estado__in=ejecutable_estados)


class Convocatory(models.Model):
    """Convocatory model (extended from stub)."""

    # UUID as primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Tipo(models.TextChoices):
        CERRADA = "cerrada", _("Cerrada")
        PUBLICA = "publica", _("Pública")
        MERITO = "merito", _("Por mérito")
        VULNERABILIDAD = "vulnerabilidad", _("Por vulnerabilidad")
        AREA_PRIORITARIA = "area_prioritaria", _("Área prioritaria")

    class Estado(models.TextChoices):
        BORRADOR = "borrador", _("Borrador")
        PUBLICADA = "publicada", _("Publicada")
        EN_INSCRIPCION = "en_inscripcion", _("En inscripción")
        EN_VERIFICACION = "en_verificacion", _("En verificación")
        EN_CALIFICACION = "en_calificacion", _("En calificación")
        DEFINITIVA = "definitiva", _("Definitiva")
        CERRADA = "cerrada", _("Cerrada")
        CANCELADA = "cancelada", _("Cancelada")

    # Keep existing name field for compatibility (renamed to nombre for consistency)
    nombre = models.CharField(
        _("nombre"),
        max_length=200,
        help_text=_("Nombre de la convocatoria"),
    )

    # New definitive fields
    codigo = models.SlugField(
        _("código"),
        max_length=32,
        unique=True,
        help_text=_("Código único de identificación (slug)"),
    )
    tipo = models.CharField(
        _("tipo"),
        max_length=16,
        choices=Tipo.choices,
        default=Tipo.PUBLICA,
        help_text=_("Tipo de convocatoria"),
    )
    periodo = models.CharField(
        _("periodo"),
        max_length=20,
        help_text=_("Periodo académico (ej: 2026-1)"),
    )
    fecha_apertura = models.DateTimeField(
        _("fecha de apertura"),
        null=True,
        blank=True,
        help_text=_("Fecha y hora de apertura de la convocatoria"),
    )
    fecha_cierre = models.DateTimeField(
        _("fecha de cierre"),
        null=True,
        blank=True,
        help_text=_("Fecha y hora de cierre de la convocatoria"),
    )
    fecha_publicacion_preliminar = models.DateTimeField(
        _("fecha de publicación preliminar"),
        null=True,
        blank=True,
        help_text=_("Fecha de publicación de resultados preliminares"),
    )
    fecha_publicacion_definitiva = models.DateTimeField(
        _("fecha de publicación definitiva"),
        null=True,
        blank=True,
        help_text=_("Fecha de publicación de resultados definitivos"),
    )
    modalidad_apoyo = models.ForeignKey(
        ModalidadApoyo,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name=_("modalidad de apoyo"),
        help_text=_("Modalidad de apoyo configurada para esta convocatoria"),
    )
    monto_semestre_smlmv = models.DecimalField(
        _("monto por semestre (SMLMV)"),
        max_digits=5,
        decimal_places=2,
        default=5.0,
        help_text=_("Monto máximo por semestre expresado en SMLMV"),
    )
    duracion_maxima_semestres = models.PositiveIntegerField(
        _("duración máxima (semestres)"),
        default=10,
        help_text=_("Duración máxima del beneficio en semestres"),
    )
    cupo_total = models.PositiveIntegerField(
        _("cupo total"),
        default=0,
        help_text=_("Cupo total de beneficiarios para esta convocatoria"),
    )
    estado = models.CharField(
        _("estado"),
        max_length=16,
        choices=Estado.choices,
        default=Estado.BORRADOR,
        help_text=_("Estado actual de la convocatoria"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="convocatorias_creadas",
        verbose_name=_("creado por"),
        null=True,
        help_text=_("Usuario que creó la convocatoria"),
    )
    created_at = models.DateTimeField(
        _("fecha de creación"),
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        _("fecha de actualización"),
        auto_now=True,
    )

    # Managers
    objects = models.Manager()
    activas = ActivasManager()

    class Meta:
        verbose_name = _("convocatoria")
        verbose_name_plural = _("convocatorias")
        ordering = ["-created_at"]

    def __str__(self):
        return self.codigo

    # Backward compatibility alias
    @property
    def name(self):
        return self.nombre

    @name.setter
    def name(self, value):
        self.nombre = value

    def clean(self):
        """Validate business rules."""
        super().clean()

        # Validate fecha ranges if provided
        if self.fecha_apertura and self.fecha_cierre:
            if self.fecha_cierre <= self.fecha_apertura:
                raise ValidationError({
                    "fecha_cierre": _("La fecha de cierre debe ser posterior a la fecha de apertura.")
                })

        if self.fecha_publicacion_preliminar and self.fecha_publicacion_definitiva:
            if self.fecha_publicacion_definitiva <= self.fecha_publicacion_preliminar:
                raise ValidationError({
                    "fecha_publicacion_definitiva": _("La fecha de publicación definitiva debe ser posterior a la fecha de publicación preliminar.")
                })


class ConfiguracionConvocatoria(models.Model):
    """Configuration/recipe for a convocatory (1:1 relationship)."""

    convocatoria = models.OneToOneField(
        Convocatory,
        on_delete=models.CASCADE,
        related_name="config",
        verbose_name=_("convocatoria"),
    )
    schema_version = models.CharField(
        _("versión del esquema"),
        max_length=8,
        default="1.0.0",
        help_text=_("Versión del esquema del payload (para migraciones)"),
    )
    payload = models.JSONField(
        _("payload"),
        default=dict,
        help_text=_("Configuración de la receta en formato JSON"),
    )
    descripcion = models.TextField(
        _("descripción"),
        blank=True,
        default="",
        help_text=_("Descripción de esta configuración"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="configuraciones_creadas",
        verbose_name=_("creado por"),
        null=True,
        help_text=_("Usuario que creó esta configuración"),
    )
    created_at = models.DateTimeField(
        _("fecha de creación"),
        auto_now_add=True,
    )
    valida_hasta = models.DateTimeField(
        _("válida hasta"),
        null=True,
        blank=True,
        help_text=_("Fecha hasta la cual esta configuración es válida (null = vigente)"),
    )

    class Meta:
        verbose_name = _("configuración de convocatoria")
        verbose_name_plural = _("configuraciones de convocatorias")
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.convocatoria.codigo} - v{self.schema_version}"

    def clean(self):
        """Validate configuration with domain rules."""
        super().clean()
        # Import here to avoid circular imports
        from .domain.validators import validar_receta
        validar_receta(self)


class Hito(models.Model):
    """Milestone/timeline item for a convocatory configuration."""

    config = models.ForeignKey(
        ConfiguracionConvocatoria,
        on_delete=models.CASCADE,
        related_name="hitos",
        verbose_name=_("configuración"),
    )
    codigo = models.SlugField(
        _("código"),
        max_length=32,
        blank=False,
        help_text=_("Código único del hito dentro de la configuración"),
    )
    orden = models.PositiveIntegerField(
        _("orden"),
        default=1,
        help_text=_("Orden de ejecución del hito"),
    )
    fecha_inicio = models.DateTimeField(
        _("fecha de inicio"),
        help_text=_("Fecha y hora de inicio del hito"),
    )
    fecha_fin = models.DateTimeField(
        _("fecha de fin"),
        help_text=_("Fecha y hora de fin del hito"),
    )
    responsable = models.CharField(
        _("responsable"),
        max_length=50,
        help_text=_("Rol o actor responsable de este hito"),
    )

    class Meta:
        verbose_name = _("hito")
        verbose_name_plural = _("hitos")
        ordering = ["config", "orden"]
        constraints = [
            models.UniqueConstraint(
                fields=["config", "codigo"],
                name="unique_hito_codigo_per_config",
            ),
            models.UniqueConstraint(
                fields=["config", "orden"],
                name="unique_hito_orden_per_config",
            ),
        ]

    def __str__(self):
        return f"{self.config.convocatoria.codigo} - {self.codigo}"

    def clean(self):
        """Validate hito dates."""
        super().clean()

        if self.fecha_fin <= self.fecha_inicio:
            raise ValidationError({
                "fecha_fin": _("La fecha de fin debe ser posterior a la fecha de inicio.")
            })


class Cupo(models.Model):
    """Quota allocation for a convocatory configuration."""

    config = models.ForeignKey(
        ConfiguracionConvocatoria,
        on_delete=models.CASCADE,
        related_name="cupos",
        verbose_name=_("configuración"),
    )
    municipio = models.ForeignKey(
        MunicipioIsla,
        on_delete=models.PROTECT,
        verbose_name=_("municipio/isla"),
        help_text=_("Municipio o isla del Archipiélago"),
    )
    modalidad = models.ForeignKey(
        ModalidadApoyo,
        on_delete=models.PROTECT,
        verbose_name=_("modalidad de apoyo"),
        help_text=_("Modalidad de apoyo"),
    )
    nivel = models.ForeignKey(
        NivelFormacion,
        on_delete=models.PROTECT,
        verbose_name=_("nivel de formación"),
        help_text=_("Nivel de formación"),
    )
    cantidad = models.PositiveIntegerField(
        _("cantidad"),
        default=1,
        help_text=_("Cantidad de cupos asignados"),
    )
    regla_especial = models.CharField(
        _("regla especial"),
        max_length=50,
        blank=True,
        default="",
        help_text=_("Regla especial aplicable a este cupo (ej: providencia_segundo_mejor)"),
    )

    class Meta:
        verbose_name = _("cupo")
        verbose_name_plural = _("cupos")
        ordering = ["config", "municipio", "modalidad", "nivel"]
        constraints = [
            models.UniqueConstraint(
                fields=["config", "municipio", "modalidad", "nivel"],
                name="unique_cupo_per_combination",
            ),
        ]

    def __str__(self):
        return f"{self.config.convocatoria.codigo} - {self.municipio.codigo}/{self.modalidad.codigo}/{self.nivel.codigo}: {self.cantidad}"


class ConvocatoriaVersion(models.Model):
    """Append-only version history for convocatory configurations."""

    convocatoria = models.ForeignKey(
        Convocatory,
        on_delete=models.CASCADE,
        related_name="versiones",
        verbose_name=_("convocatoria"),
    )
    version = models.PositiveIntegerField(
        _("versión"),
        help_text=_("Número de versión (se incrementa automáticamente)"),
    )
    schema_version = models.CharField(
        _("versión del esquema"),
        max_length=8,
        default="1.0.0",
        help_text=_("Versión del esquema del snapshot"),
    )
    snapshot = models.JSONField(
        _("snapshot"),
        help_text=_("Snapshot completo de la configuración en el momento de la versión"),
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="versiones_creadas",
        verbose_name=_("creado por"),
        null=True,
        help_text=_("Usuario que creó esta versión"),
    )
    created_at = models.DateTimeField(
        _("fecha de creación"),
        auto_now_add=True,
    )
    valida_hasta = models.DateTimeField(
        _("válida hasta"),
        null=True,
        blank=True,
        help_text=_("Fecha hasta la cual esta versión es válida"),
    )

    class Meta:
        verbose_name = _("versión de convocatoria")
        verbose_name_plural = _("versiones de convocatorias")
        ordering = ["convocatoria", "-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["convocatoria", "version"],
                name="unique_version_per_convocatoria",
            ),
        ]

    def __str__(self):
        return f"{self.convocatoria.codigo} - v{self.version}"
