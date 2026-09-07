"""Service for FUI wizard operations."""
from django.db import transaction
from django.utils import timezone


class WizardError(Exception):
    """Error during wizard operations."""

    pass


def validar_convocatoria_abierta(convocatoria) -> bool:
    """Check if convocation is in EN_INSCRIPCION state."""
    from apps.convocatories.models import Convocatory

    return convocatoria.estado == Convocatory.Estado.EN_INSCRIPCION


def save_draft(solicitud, step: int, data: dict) -> None:
    """Save partial draft data for a wizard step.

    Args:
        solicitud: Solicitud instance
        step: Current wizard step (1-5)
        data: Dictionary of data to save

    Raises:
        WizardError: If application cannot be edited
    """
    if not solicitud.puede_editar():
        raise WizardError("La solicitud no puede ser editada en su estado actual")

    # Save data based on step
    if step == 1:
        solicitud.datos_personales = data
    elif step == 2:
        solicitud.datos_academicos = data
    elif step == 3:
        solicitud.datos_socioeconomicos = data

    solicitud.current_step = step
    solicitud.save(update_fields=[
        "datos_personales",
        "datos_academicos",
        "datos_socioeconomicos",
        "current_step",
        "updated_at",
    ])


def submit(solicitud, consentimiento: bool, actor) -> None:
    """Submit a completed FUI application.

    Args:
        solicitud: Solicitud instance
        consentimiento: User consent flag
        actor: User submitting

    Raises:
        WizardError: If validation fails
    """
    from apps.applications.models import Solicitud
    from apps.applications.services.radicado_service import generar_radicado

    # Validate state
    if not solicitud.puede_editar():
        raise WizardError("La solicitud no puede ser enviada en su estado actual")

    # Validate convocation is open
    if not validar_convocatoria_abierta(solicitud.convocatoria):
        raise WizardError("La convocatoria no está abierta para inscripciones")

    # Validate consentimiento
    if not consentimiento:
        raise WizardError("Debe aceptar el tratamiento de datos personales")

    # Validate data completeness
    if not solicitud.datos_personales.get("nombre"):
        raise WizardError("Faltan datos personales")

    if not solicitud.datos_academicos.get("programa"):
        raise WizardError("Faltan datos académicos")

    # Mark as complete first
    solicitud.estado = Solicitud.Estado.COMPLETA
    solicitud.consentimiento = True
    solicitud.consentimiento_fecha = timezone.now()

    # Generate radicado in transaction
    with transaction.atomic():
        radicado = generar_radicado()
        solicitud.radicado = radicado

        # Generate PDF (simplified - just mark as generated)
        # In full implementation, would call PDF service

        solicitud.estado = Solicitud.Estado.RADICADA
        solicitud.save()

    # Log audit event
    _log_submission(solicitud, actor)


def _log_submission(solicitud, actor) -> None:
    """Log application submission to audit (CAP-022 / CHG-801).

    Goes through ``log_audit_event(...)`` so the chain head is
    locked and the hash chain cannot fork under concurrent
    submissions (AUD-001 / AUD-003).
    """
    import logging

    from apps.audit.services import log_audit_event

    logger = logging.getLogger(__name__)

    try:
        log_audit_event(
            actor=actor,
            action="solicitud.submitted",
            entity="Solicitud",
            entity_id=solicitud.id,
            changes={
                "radicado": solicitud.radicado,
                "estado": Solicitud.Estado.RADICADA,
            },
            module="applications",
        )
    except Exception:
        # Audit failure should not block submission, but must be
        # logged so the gap is visible to operators (CHG-801).
        logger.exception("audit: solicitud submission audit log failed")
