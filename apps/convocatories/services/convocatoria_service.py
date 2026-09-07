"""Service layer for Convocatory state transitions.

This module implements the business logic for publishing, closing,
and canceling convocation, integrating with audit and notifications.
"""
from django.db import transaction
from django.utils import timezone

from apps.convocatories.domain import (
    Estado,
    transicionar,
    validar_transicion,
)


class TransitionError(Exception):
    """Error during convocation transition."""

    pass


def publicar(convocatoria, actor) -> None:
    """Publish a convocation (borrador -> publicada).

    Validates that:
    - Current state is BORRADOR
    - Convocatory has a config (CHG-104)

    Args:
        convocatoria: Convocatory instance
        actor: User performing the action

    Raises:
        ValidationError: If validation fails
    """
    from django.core.exceptions import ValidationError
    from apps.convocatories.models import ConfiguracionConvocatoria

    # Validate current state
    if convocatoria.estado != Estado.BORRADOR:
        raise ValidationError({
            "estado": f"Solo se puede publicar desde estado BORRADOR, actual: {convocatoria.estado}"
        })

    # Validate config exists (CHG-104 requirement)
    if not hasattr(convocatoria, "config") or convocatoria.config is None:
        raise ValidationError({
            "config": "La convocatoria debe tener una configuración (receta) antes de publicar"
        })

    # Execute transition
    with transaction.atomic():
        transicionar(convocatoria, Estado.PUBLICADA, actor=actor)

        # Audit log
        _log_transition(convocatoria, actor, "published")

        # Send notification (CHG-106)
        _send_notification(
            user=actor,
            title="Convocatoria publicada",
            message=f"La convocatoria {convocatoria.codigo} ha sido publicada.",
            event="convocatoria.publicada",
        )


def cerrar(convocatoria, actor) -> None:
    """Close a convocation (definitiva -> cerrada).

    Validates that:
    - Current state is DEFINITIVA

    Args:
        convocatoria: Convocatory instance
        actor: User performing the action

    Raises:
        ValidationError: If validation fails
    """
    from django.core.exceptions import ValidationError

    # Validate current state
    if convocatoria.estado != Estado.DEFINITIVA:
        raise ValidationError({
            "estado": f"Solo se puede cerrar desde estado DEFINITIVA, actual: {convocatoria.estado}"
        })

    # Execute transition
    with transaction.atomic():
        transicionar(convocatoria, Estado.CERRADA, actor=actor)

        # Audit log
        _log_transition(convocatoria, actor, "closed")

        # Send notification (CHG-106)
        _send_notification(
            user=actor,
            title="Convocatoria cerrada",
            message=f"La convocatoria {convocatoria.codigo} ha sido cerrada.",
            event="convocatoria.cerrada",
        )


def cancelar(convocatoria, actor, motivo: str) -> None:
    """Cancel a convocation (from any active state -> cancelada).

    Args:
        convocatoria: Convocatory instance
        actor: User performing the action
        motivo: Reason for cancellation

    Raises:
        ValidationError: If validation fails
    """
    from django.core.exceptions import ValidationError

    # Validate current state is active (not terminal)
    if convocatoria.estado in {Estado.CERRADA, Estado.CANCELADA}:
        raise ValidationError({
            "estado": f"No se puede cancelar una convocatoria en estado {convocatoria.estado}"
        })

    # Execute transition
    with transaction.atomic():
        transicionar(convocatoria, Estado.CANCELADA, actor=actor, motivo=motivo)

        # Audit log
        _log_transition(convocatoria, actor, "cancelled", motivo)


def transicionar_estado(convocatoria, estado_destino: str, actor, motivo: str = "") -> None:
    """Generic state transition with validation.

    Args:
        convocatoria: Convocatory instance
        estado_destino: Target state
        actor: User performing the action
        motivo: Reason (required for CANCELADA)

    Raises:
        ValidationError: If transition is not allowed
    """
    from django.core.exceptions import ValidationError

    # Validate transition
    es_valida, error_code = validar_transicion(convocatoria.estado, estado_destino)

    if not es_valida:
        raise ValidationError({
            "estado": f"Transición no permitida: {convocatoria.estado} → {estado_destino}"
        })

    # Execute with audit and notifications
    with transaction.atomic():
        transicionar(convocatoria, estado_destino, actor=actor, motivo=motivo)

        # Audit
        _log_transition(convocatoria, actor, estado_destino, motivo)


def _log_transition(convocatoria, actor, accion: str, motivo: str = "") -> None:
    """Log transition to audit (CHG-102 / CHG-801).

    Writes via ``log_audit_event(...)`` so the chain head is locked
    and the hash chain cannot fork under concurrent transitions
    (AUD-001 / AUD-003).
    """
    import logging

    from apps.audit.services import log_audit_event

    logger = logging.getLogger(__name__)

    # Action must fit the 20-char cap on the AuditEvent column. Drop
    # the "convocatory." prefix to keep room for verb forms.
    action = f"conv.{accion}" if len(accion) <= 16 else accion[:20]

    try:
        log_audit_event(
            actor=actor,
            action=action,
            entity="Convocatory",
            entity_id=convocatoria.id,
            changes={
                "estado": {
                    "from": getattr(convocatoria, "_previous_estado", None),
                    "to": convocatoria.estado,
                },
                "motivo": motivo,
            },
            module="convocatories",
        )
    except Exception:
        # Audit failure should not block the transition, but must
        # be logged loudly for operators (CHG-801).
        logger.exception("audit: convocatoria transition audit log failed")


def _send_notification(user, title: str, message: str, event: str) -> None:
    """Send notification (CHG-106 integration)."""
    try:
        from apps.accounts.services.notifications import get_notifier

        notifier = get_notifier()
        if notifier:
            notifier.notify(
                recipient=user,
                title=title,
                message=message,
                event=event,
            )
    except Exception:
        # Notification failure should not block the transition
        pass
