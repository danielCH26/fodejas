"""Selectors for domain catalogs."""
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


def get_estratos_activos():
    """Return active estratos ordered by orden."""
    return Estrato.activos.all()


def get_grupos_sisben_activos():
    """Return active grupos SISBÉN ordered by orden."""
    return GrupoSisben.activos.all()


def get_etnias_activas():
    """Return active etnias ordered by orden."""
    return Etnia.activos.all()


def get_municipios_islas_activos():
    """Return active municipios/islas ordered by orden."""
    return MunicipioIsla.activos.all()


def get_niveles_formacion_activos():
    """Return active niveles de formación ordered by orden."""
    return NivelFormacion.activos.all()


def get_modalidades_apoyo_activas():
    """Return active modalidades de apoyo ordered by orden."""
    return ModalidadApoyo.activos.all()


def get_tipos_ies_activos():
    """Return active tipos de IES ordered by orden."""
    return TipoIes.activos.all()


def get_tipos_documento_activos():
    """Return active tipos de documento ordered by orden."""
    return TipoDocumento.activos.all()


def get_estados_documento_activos():
    """Return active estados de documento ordered by orden."""
    return EstadoDocumento.activos.all()


def get_causales_terminacion_convenio_activos():
    """Return active causales de terminación ordered by orden."""
    return CausalTerminacionConvenio.activos.all()
