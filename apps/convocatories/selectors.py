"""Selectors for retrieving convocatory data.

These selectors provide optimized queries for fetching configuration data
with proper prefetching.
"""

from django.db.models import Q
from django.utils import timezone

from .models import (
    ConfiguracionConvocatoria,
    ConvocatoriaVersion,
    Convocatory,
)


def get_convocatoria_vigente(convocatoria_id: int) -> Convocatory | None:
    """Get a convocatory that is currently active (not closed/cancelled).

    Args:
        convocatoria_id: ID of the convocatory

    Returns:
        Convocatory instance if found and active, None otherwise
    """
    return Convocatory.objects.activas().filter(pk=convocatoria_id).first()


def get_receta_vigente(convocatoria_id: int) -> ConfiguracionConvocatoria | None:
    """Get the current active recipe for a convocatory.

    Returns the configuration with hitos and cupos prefetched
    for optimal query performance.

    Args:
        convocatoria_id: ID of the convocatory

    Returns:
        ConfiguracionConvocatoria instance with prefetched relations,
        or None if not found
    """
    return (
        ConfiguracionConvocatoria.objects.select_related("convocatoria")
        .prefetch_related("hitos", "cupos")
        .filter(convocatoria_id=convocatoria_id)
        .filter(Q(valida_hasta__isnull=True) | Q(valida_hasta__gte=timezone.now()))
        .first()
    )


def get_convocatoria_by_codigo(codigo: str) -> Convocatory | None:
    """Get a convocatory by its code.

    Args:
        codigo: The unique code of the convocatory

    Returns:
        Convocatory instance if found, None otherwise
    """
    return Convocatory.objects.filter(codigo=codigo).first()


def get_versiones(convocatoria_id: int) -> list[ConvocatoriaVersion]:
    """Get all versions for a convocatory.

    Returns versions ordered by version number descending.

    Args:
        convocatoria_id: ID of the convocatory

    Returns:
        List of ConvocatoriaVersion instances
    """
    return list(
        ConvocatoriaVersion.objects.filter(convocatoria_id=convocatoria_id).order_by("-version")
    )


def get_version_activa(convocatoria_id: int) -> ConvocatoriaVersion | None:
    """Get the currently active version for a convocatory.

    Args:
        convocatoria_id: ID of the convocatory

    Returns:
        ConvocatoriaVersion instance that is currently active, None if none
    """
    return (
        ConvocatoriaVersion.objects.filter(convocatoria_id=convocatoria_id)
        .filter(Q(valida_hasta__isnull=True) | Q(valida_hasta__gte=timezone.now()))
        .order_by("-version")
        .first()
    )


def get_configuracion(convocatoria_id: int) -> ConfiguracionConvocatoria | None:
    """Get the configuration for a convocatory (without version filtering).

    Args:
        convocatoria_id: ID of the convocatory

    Returns:
        ConfiguracionConvocatoria instance if exists, None otherwise
    """
    return (
        ConfiguracionConvocatoria.objects.select_related("convocatoria")
        .prefetch_related("hitos", "cupos")
        .filter(convocatoria_id=convocatoria_id)
        .first()
    )
