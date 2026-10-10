"""Admin configuration for core models."""
from django.contrib import admin

from .models import (
    CausalTerminacionConvenio,
    EstadoDocumento,
    Estrato,
    Etnia,
    GrupoSisben,
    ModalidadApoyo,
    MunicipioIsla,
    NivelFormacion,
    TipoDocumento,
    TipoIes,
)


class CatalogoAdmin(admin.ModelAdmin):
    """Base admin for all catalog models."""
    list_display = ('codigo', 'nombre', 'activo', 'orden')
    list_filter = ('activo',)
    search_fields = ('codigo', 'nombre')
    ordering = ('orden', 'nombre')


@admin.register(Estrato)
class EstratoAdmin(CatalogoAdmin):
    pass


@admin.register(GrupoSisben)
class GrupoSisbenAdmin(CatalogoAdmin):
    pass


@admin.register(Etnia)
class EtniaAdmin(CatalogoAdmin):
    pass


@admin.register(MunicipioIsla)
class MunicipioIslaAdmin(CatalogoAdmin):
    pass


@admin.register(NivelFormacion)
class NivelFormacionAdmin(CatalogoAdmin):
    pass


@admin.register(ModalidadApoyo)
class ModalidadApoyoAdmin(CatalogoAdmin):
    pass


@admin.register(TipoIes)
class TipoIesAdmin(CatalogoAdmin):
    pass


@admin.register(TipoDocumento)
class TipoDocumentoAdmin(CatalogoAdmin):
    pass


@admin.register(EstadoDocumento)
class EstadoDocumentoAdmin(CatalogoAdmin):
    pass


@admin.register(CausalTerminacionConvenio)
class CausalTerminacionConvenioAdmin(CatalogoAdmin):
    pass
