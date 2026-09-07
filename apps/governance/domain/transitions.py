"""Domain transitions for governance (CHG-208).

Pure domain functions for state-machine transitions of
``ActoAdministrativo``. Vistas (``apps.governance.views``) only
orchestrate these; they MUST NOT call ``objects.update()`` /
``objects.create()`` directly for transitions.

Per AGENTS.md §6 regla 6, business logic lives in ``services/`` /
``domain/`` and NEVER in views or templates.
"""
from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.governance.models import ActoAdministrativo
from apps.governance.services.generador import generar_numero_acto


def firmar_acto(acto_uuid, firmantes: list[str], usuario=None) -> ActoAdministrativo:
    """Transition ``ActoAdministrativo`` from BORRADOR to FIRMADO.

    Args:
        acto_uuid: ``uuid.UUID`` (the public ``uuid`` field, not the
            internal ``id`` PK) of the acto to sign.
        firmantes: list of strings naming the people who signed.
        usuario: optional ``User`` instance, recorded via the audit
            signal (CHG-801) but not persisted on the acto itself
            (the acto's ``firmantes`` field is the canonical record).

    Returns:
        The signed ``ActoAdministrativo``.

    Raises:
        ValueError: if the acto does not exist or is not in BORRADOR.
    """
    if not firmantes:
        raise ValueError("firmar_acto requiere al menos un firmante")
    with transaction.atomic():
        try:
            acto = (
                ActoAdministrativo.objects
                .select_for_update()
                .get(uuid=acto_uuid)
            )
        except ActoAdministrativo.DoesNotExist as exc:
            raise ValueError(f"acto {acto_uuid} no existe") from exc
        if acto.estado != ActoAdministrativo.Estado.BORRADOR:
            raise ValueError(
                f"solo se pueden firmar actos en BORRADOR; "
                f"acto {acto.uuid} está en {acto.estado}"
            )
        acto.estado = ActoAdministrativo.Estado.FIRMADO
        acto.firmantes = list(firmantes)
        acto.fecha_firma = timezone.now()
        acto.save(update_fields=["estado", "firmantes", "fecha_firma", "updated_at"])
        return acto


def crear_modificatorio(
    acto_original_uuid,
    asunto: str,
    considerandos: list[dict[str, Any]],
    resolutivo: str,
    fecha_expedicion=None,
    firmantes_iniciales: list[str] | None = None,
) -> ActoAdministrativo:
    """Create a CPACA Art. 45 acto modificatorio of an existing acto.

    The modificatorio inherits the ``convocatoria`` of the original
    and is generated with a separate ``SecuencialActo`` sequence per
    year (so modificatorios, resoluciones, actas each have their own
    counter).

    Args:
        acto_original_uuid: ``uuid.UUID`` (the public ``uuid`` field)
            of the original acto.
        asunto, considerandos, resolutivo: standard acto content.
        fecha_expedicion: optional ``date``; defaults to today.
        firmantes_iniciales: optional pre-fill for the firmantes JSON
            field (acts as a draft hint; the acto still has to be
            signed explicitly via ``firmar_acto``).

    Returns:
        The newly-created ``ActoAdministrativo`` in BORRADOR state.

    Raises:
        ValueError: if the original does not exist or is itself a
            modificatorio (chains of modificatorios are forbidden).
    """
    with transaction.atomic():
        try:
            original = (
                ActoAdministrativo.objects
                .select_for_update()
                .get(uuid=acto_original_uuid)
            )
        except ActoAdministrativo.DoesNotExist as exc:
            raise ValueError(
                f"acto original {acto_original_uuid} no existe"
            ) from exc
        if original.tipo == ActoAdministrativo.Tipo.MODIFICATORIO:
            raise ValueError(
                "no se puede crear un modificatorio de otro modificatorio "
                "(CPACA Art. 45 admite un solo nivel)"
            )
        numero = generar_numero_acto(ActoAdministrativo.Tipo.MODIFICATORIO)
        if fecha_expedicion is None:
            fecha_expedicion = timezone.now().date()
        modificatorio = ActoAdministrativo.objects.create(
            numero=numero,
            tipo=ActoAdministrativo.Tipo.MODIFICATORIO,
            fecha_expedicion=fecha_expedicion,
            asunto=asunto,
            considerandos=considerandos,
            resolutivo=resolutivo,
            convocatoria=original.convocatoria,
            acto_original=original,
            estado=ActoAdministrativo.Estado.BORRADOR,
            firmantes=list(firmantes_iniciales or []),
        )
        return modificatorio
