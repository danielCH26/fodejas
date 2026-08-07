"""Receta (configuration) service for publishing and reverting versions.

This service handles the publish/revert workflow for convocatory configurations
as defined in the design document.
"""
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import CustomUser

from ..models import (
    ConfiguracionConvocatoria,
    ConvocatoriaVersion,
    Convocatory,
    Cupo,
    Hito,
)


def publicar_version(
    convocatoria: Convocatory,
    created_by: CustomUser | None = None,
) -> ConvocatoriaVersion:
    """Publish a new version of the configuration (snapshot).

    Creates an immutable snapshot of the current configuration (payload + hitos + cupos)
    and increments the version number.

    Args:
        convocatoria: The Convocatory to publish
        created_by: User publishing the version

    Returns:
        ConvocatoriaVersion: The newly created version snapshot

    Raises:
        ValueError: If the convocatoria doesn't have a configuration
    """
    try:
        config = convocatoria.config
    except ConfiguracionConvocatoria.DoesNotExist as err:
        raise ValueError("La convocatoria no tiene configuración para publicar") from err

    # Get the latest version number
    latest_version = ConvocatoriaVersion.objects.filter(
        convocatoria=convocatoria
    ).order_by("-version").first()

    new_version_number = (latest_version.version + 1) if latest_version else 1

    # Build snapshot data
    snapshot_data = {
        "payload": config.payload,
        "schema_version": config.schema_version,
        "hitos": [
            {
                "codigo": h.codigo,
                "orden": h.orden,
                "fecha_inicio": h.fecha_inicio.isoformat(),
                "fecha_fin": h.fecha_fin.isoformat(),
                "responsable": h.responsable,
            }
            for h in config.hitos.all()
        ],
        "cupos": [
            {
                "municipio_id": c.municipio_id,
                "modalidad_id": c.modalidad_id,
                "nivel_id": c.nivel_id,
                "cantidad": c.cantidad,
                "regla_especial": c.regla_especial,
            }
            for c in config.cupos.all()
        ],
    }

    with transaction.atomic():
        # Mark previous versions as expired
        ConvocatoriaVersion.objects.filter(
            convocatoria=convocatoria,
            valida_hasta__isnull=True
        ).update(valida_hasta=timezone.now())

        # Create new version
        version = ConvocatoriaVersion.objects.create(
            convocatoria=convocatoria,
            version=new_version_number,
            schema_version=config.schema_version,
            snapshot=snapshot_data,
            created_by=created_by,
        )

    return version


def revertir_version(
    version: ConvocatoriaVersion,
    created_by: CustomUser | None = None,
) -> ConfiguracionConvocatoria:
    """Revert configuration to a previous version.

    Restores the configuration from a version snapshot.

    Args:
        version: The ConvocatoriaVersion to revert to
        created_by: User performing the revert

    Returns:
        ConfiguracionConvocatoria: The updated configuration

    Note:
        This creates a new version (doesn't delete history).
        The reverted configuration becomes the new "live" version.
    """
    snapshot = version.snapshot
    config = version.convocatoria.config

    with transaction.atomic():
        # Update config from snapshot
        config.payload = snapshot.get("payload", {})
        config.schema_version = snapshot.get("schema_version", "1.0.0")
        config.save()

        # Clear and recreate hitos
        config.hitos.all().delete()
        for hito_data in snapshot.get("hitos", []):
            Hito.objects.create(
                config=config,
                codigo=hito_data["codigo"],
                orden=hito_data["orden"],
                fecha_inicio=hito_data["fecha_inicio"],
                fecha_fin=hito_data["fecha_fin"],
                responsable=hito_data["responsable"],
            )

        # Clear and recreate cupos
        config.cupos.all().delete()

        for cupo_data in snapshot.get("cupos", []):
            Cupo.objects.create(
                config=config,
                municipio_id=cupo_data["municipio_id"],
                modalidad_id=cupo_data["modalidad_id"],
                nivel_id=cupo_data["nivel_id"],
                cantidad=cupo_data["cantidad"],
                regla_especial=cupo_data.get("regla_especial", ""),
            )

        # Publish a new version documenting the revert
        publicar_version(version.convocatoria, created_by)

    return config


def clonar_receta(
    source_convocatoria: Convocatory,
    target_convocatoria: Convocatory,
    created_by: CustomUser | None = None,
) -> ConfiguracionConvocatoria:
    """Clone a recipe from one convocatoria to another.

    Copies the configuration (payload + hitos + cupos) to a new convocatoria.

    Args:
        source_convocatoria: The source Convocatory to clone from
        target_convocatoria: The target Convocatory to clone to
        created_by: User performing the clone

    Returns:
        ConfiguracionConvocatoria: The newly created configuration for target
    """
    source_config = source_convocatoria.config

    with transaction.atomic():
        # Create new config for target
        target_config = ConfiguracionConvocatoria.objects.create(
            convocatoria=target_convocatoria,
            schema_version=source_config.schema_version,
            payload=source_config.payload,
            descripcion=f"Clon de {source_convocatoria.codigo}",
            created_by=created_by,
        )

        # Clone hitos
        for hito in source_config.hitos.all():
            Hito.objects.create(
                config=target_config,
                codigo=hito.codigo,
                orden=hito.orden,
                fecha_inicio=hito.fecha_inicio,
                fecha_fin=hito.fecha_fin,
                responsable=hito.responsable,
            )

        # Clone cupos
        for cupo in source_config.cupos.all():
            Cupo.objects.create(
                config=target_config,
                municipio_id=cupo.municipio_id,
                modalidad_id=cupo.modalidad_id,
                nivel_id=cupo.nivel_id,
                cantidad=cupo.cantidad,
                regla_especial=cupo.regla_especial,
            )

    return target_config
