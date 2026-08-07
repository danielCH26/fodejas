from django.db import models


class ActivosManager(models.Manager):
    """Manager that filters only active records."""
    def get_queryset(self):
        # Apply ordering from model's Meta if available
        qs = super().get_queryset().filter(activo=True)
        if self.model._meta.ordering:
            qs = qs.order_by(*self.model._meta.ordering)
        return qs


class CatalogoDominio(models.Model):
    """Abstract base model for domain catalogs."""
    codigo = models.SlugField(max_length=32, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, default="")
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)
    metadatos = models.JSONField(default=dict, blank=True)
    
    objects = models.Manager()      # all rows
    activos = ActivosManager()      # activo=True only
    
    class Meta:
        abstract = True
        ordering = ["orden", "nombre"]
    
    def __str__(self):
        return self.nombre


class Estrato(CatalogoDominio):
    """Estrato socioeconómico (1-6)."""
    class Meta:
        verbose_name = "Estrato"
        verbose_name_plural = "Estratos"
        ordering = ["orden", "nombre"]


class GrupoSisben(CatalogoDominio):
    """Grupo SISBÉN (A-D)."""
    class Meta:
        verbose_name = "Grupo SISBÉN"
        verbose_name_plural = "Grupos SISBÉN"
        ordering = ["orden", "nombre"]


class Etnia(CatalogoDominio):
    """Etnia/pertinencia étnica."""
    class Meta:
        verbose_name = "Etnia"
        verbose_name_plural = "Etnias"
        ordering = ["orden", "nombre"]


class MunicipioIsla(CatalogoDominio):
    """Municipio/Isla del Archipiélago."""
    class Meta:
        verbose_name = "Municipio/Isla"
        verbose_name_plural = "Municipios/Islas"
        ordering = ["orden", "nombre"]


class NivelFormacion(CatalogoDominio):
    """Nivel de formación (técnico, tecnológico, pregrado, etc.)."""
    class Meta:
        verbose_name = "Nivel de Formación"
        verbose_name_plural = "Niveles de Formación"
        ordering = ["orden", "nombre"]


class ModalidadApoyo(CatalogoDominio):
    """Modalidad de apoyo (crédito, beca, préstamo)."""
    class Meta:
        verbose_name = "Modalidad de Apoyo"
        verbose_name_plural = "Modalidades de Apoyo"
        ordering = ["orden", "nombre"]


class TipoIes(CatalogoDominio):
    """Tipo de Institución de Educación Superior."""
    class Meta:
        verbose_name = "Tipo de IES"
        verbose_name_plural = "Tipos de IES"
        ordering = ["orden", "nombre"]


class TipoDocumento(CatalogoDominio):
    """Tipo de documento de identidad."""
    class Meta:
        verbose_name = "Tipo de Documento"
        verbose_name_plural = "Tipos de Documento"
        ordering = ["orden", "nombre"]


class EstadoDocumento(CatalogoDominio):
    """Estado de validación de documento."""
    class Meta:
        verbose_name = "Estado de Documento"
        verbose_name_plural = "Estados de Documento"
        ordering = ["orden", "nombre"]


class CausalTerminacionConvenio(CatalogoDominio):
    """Causal de terminación de convenio."""
    class Meta:
        verbose_name = "Causal de Terminación de Convenio"
        verbose_name_plural = "Causales de Terminación de Convenio"
        ordering = ["orden", "nombre"]