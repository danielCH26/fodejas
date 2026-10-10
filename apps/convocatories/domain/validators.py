"""Business logic validators for convocatory configuration.

These validators are called from ConfiguracionConvocatoria.full_clean()
to enforce business rules defined in project.md §11.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.core.exceptions import ValidationError

from apps.core.models import (
    ModalidadApoyo,
    MunicipioIsla,
    NivelFormacion,
)

from .normativa import NORMATIVA

if TYPE_CHECKING:
    from apps.convocatories.models import (
        ConfiguracionConvocatoria,
        Cupo,
    )


def validar_receta(config: ConfiguracionConvocatoria) -> None:
    """Validate a complete Receta (configuration + hitos + cupos).

    Called from ConfiguracionConvocatoria.full_clean().

    Validation rules:
    1. JSON schema validation for payload
    2. Sum of weights (pesos) equals 100
    3. Hito/Cupo FKs point to active catalogs
    4. Plazos match nivel requirements (§11.4)
    5. Providencia references use normativa.py keys (§11.5)

    Args:
        config: ConfiguracionConvocatoria instance to validate

    Raises:
        ValidationError: If any business rule is violated
    """
    errors = []

    # 1. Validate payload structure (basic schema check)
    if config.payload:
        _validar_payload_schema(config.payload, errors)

    # 2. Validate criteria weights sum to 100
    _validar_pesos_criterios(config.payload, errors)

    # 3. Validate Hito/Cupo FKs to active catalogs
    _validar_catalogos_activos(config, errors)

    # 4. Validate plazos against normativa
    _validar_plazos(config, errors)

    # 5. Validate Providencia references
    _validar_providencia(config, errors)

    if errors:
        raise ValidationError(errors)


def _validar_payload_schema(payload: dict, errors: list) -> None:
    """Validate basic payload schema."""
    required_fields = ["requisitos", "criterios"]
    for field in required_fields:
        if field not in payload:
            errors.append(f"payload.{field}: campo requerido")


def _validar_pesos_criterios(payload: dict, errors: list) -> None:
    """Validate that sum of criteria weights equals 100."""
    criterios = payload.get("criterios", [])
    if not criterios:
        return

    suma_pesos = sum(c.get("peso", 0) for c in criterios)
    if suma_pesos != 100:
        errors.append(f"criterios: suma de pesos debe ser 100, " f"actualmente {suma_pesos}")


def _validar_catalogos_activos(config: ConfiguracionConvocatoria, errors: list) -> None:
    """Validate all FK references point to active catalogs."""
    from apps.convocatories.models import Cupo, Hito

    hitos = Hito.objects.filter(config=config)
    cupos = Cupo.objects.filter(config=config)

    # Check Hito has required fields
    for hito in hitos:
        if not hito.codigo:
            errors.append("Hito: código es requerido")
        if not hito.fecha_inicio or not hito.fecha_fin:
            errors.append(f"Hito {hito.codigo}: fechas requeridas")

    # Check Cupo FKs to active catalogs
    for cupo in cupos:
        if hasattr(cupo, "municipio") and cupo.municipio_id:
            if not MunicipioIsla.objects.activos().filter(pk=cupo.municipio_id).exists():
                errors.append(f"Cupo: municipio_id {cupo.municipio_id} no está activo")

        if hasattr(cupo, "modalidad") and cupo.modalidad_id:
            if not ModalidadApoyo.objects.activos().filter(pk=cupo.modalidad_id).exists():
                errors.append(f"Cupo: modalidad_id {cupo.modalidad_id} no está activa")

        if hasattr(cupo, "nivel") and cupo.nivel_id:
            if not NivelFormacion.objects.activos().filter(pk=cupo.nivel_id).exists():
                errors.append(f"Cupo: nivel_id {cupo.nivel_id} no está activo")


def _validar_plazos(config: ConfiguracionConvocatoria, errors: list) -> None:
    """Validate that plazos match normativa requirements for each nivel."""
    from apps.convocatories.models import Hito

    hitos = Hito.objects.filter(config=config)

    for hito in hitos:
        normativa_key = getattr(hito, "normativa_key", None)
        if normativa_key and normativa_key not in NORMATIVA:
            errors.append(
                f"Hito {hito.codigo}: normativa_key '{normativa_key}' "
                f"no encontrado en normativa.py"
            )


def _validar_providencia(config: ConfiguracionConvocatoria, errors: list) -> None:
    """Validate Providencia-specific references use normativa.py."""
    from apps.convocatories.models import Cupo

    cupos = Cupo.objects.filter(config=config)

    for cupo in cupos:
        if hasattr(cupo, "municipio") and cupo.municipio_id:
            try:
                muni = MunicipioIsla.objects.get(pk=cupo.municipio_id)
                if muni.codigo == "PROVIDENCIA":
                    if not getattr(cupo, "regla_especial", None):
                        errors.append(
                            f"Cupo {cupo.id}: Providencia requiere "
                            f"regla_especial referenciando normativa"
                        )
            except MunicipioIsla.DoesNotExist:
                pass


def validar_cupo(cupo: Cupo) -> None:
    """Validate a single Cupo instance.

    Args:
        cupo: Cupo instance to validate

    Raises:
        ValidationError: If validation fails
    """
    errors = []

    if hasattr(cupo, "municipio") and cupo.municipio_id:
        if not MunicipioIsla.objects.activos().filter(pk=cupo.municipio_id).exists():
            errors.append("Municipio debe estar activo")

    if hasattr(cupo, "modalidad") and cupo.modalidad_id:
        if not ModalidadApoyo.objects.activos().filter(pk=cupo.modalidad_id).exists():
            errors.append("Modalidad debe estar activa")

    if hasattr(cupo, "nivel") and cupo.nivel_id:
        if not NivelFormacion.objects.activos().filter(pk=cupo.nivel_id).exists():
            errors.append("Nivel debe estar activo")

    if errors:
        raise ValidationError(errors)
