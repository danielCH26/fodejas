"""State machine transitions for Convocatory.

This module implements the Finite State Machine (FSM) for convocation lifecycle
as defined in CAP-002 and the CHG-201 specification.
"""
from django.core.exceptions import ValidationError


# State definitions (matches Convocatory.Estado)
class Estado:
    """Convocatory states."""

    BORRADOR = "borrador"
    PUBLICADA = "publicada"
    EN_INSCRIPCION = "en_inscripcion"
    EN_VERIFICACION = "en_verificacion"
    EN_CALIFICACION = "en_calificacion"
    DEFINITIVA = "definitiva"
    CERRADA = "cerrada"
    CANCELADA = "cancelada"

    # Terminal states (no further transitions allowed)
    TERMINAL_STATES = {CERRADA, CANCELADA}

    # Active states (can be cancelled)
    ACTIVE_STATES = {
        BORRADOR,
        PUBLICADA,
        EN_INSCRIPCION,
        EN_VERIFICACION,
        EN_CALIFICACION,
        DEFINITIVA,
    }


# Valid transitions: origin_state -> set of valid destination states
TRANSICIONES_PERMITIDAS = {
    Estado.BORRADOR: {
        Estado.PUBLICADA,
        Estado.CANCELADA,
    },
    Estado.PUBLICADA: {
        Estado.EN_INSCRIPCION,
        Estado.CANCELADA,
    },
    Estado.EN_INSCRIPCION: {
        Estado.EN_VERIFICACION,
        Estado.CANCELADA,
    },
    Estado.EN_VERIFICACION: {
        Estado.EN_CALIFICACION,
        Estado.CANCELADA,
    },
    Estado.EN_CALIFICACION: {
        Estado.DEFINITIVA,
        Estado.CANCELADA,
    },
    Estado.DEFINITIVA: {
        Estado.CERRADA,
        Estado.CANCELADA,
    },
    Estado.CERRADA: set(),  # Terminal state
    Estado.CANCELADA: set(),  # Terminal state
}


def get_estado_display(estado: str) -> str:
    """Get human-readable display for estado."""
    return {
        Estado.BORRADOR: "Borrador",
        Estado.PUBLICADA: "Publicada",
        Estado.EN_INSCRIPCION: "En Inscripción",
        Estado.EN_VERIFICACION: "En Verificación",
        Estado.EN_CALIFICACION: "En Calificación",
        Estado.DEFINITIVA: "Definitiva",
        Estado.CERRADA: "Cerrada",
        Estado.CANCELADA: "Cancelada",
    }.get(estado, estado)


def validar_transicion(estado_origen: str, estado_destino: str) -> tuple[bool, str]:
    """Validate if a state transition is allowed.

    Args:
        estado_origen: Current state of the convocation
        estado_destino: Desired new state

    Returns:
        Tuple of (is_valid, error_code)
        - is_valid: True if transition is allowed
        - error_code: Error code if invalid, empty string if valid
    """
    # Check if origin is terminal
    if estado_origen in Estado.TERMINAL_STATES:
        return False, "transition_from_terminal"

    # Check if destination is valid for origin
    permitidas = TRANSICIONES_PERMITIDAS.get(estado_origen, set())

    if estado_destino not in permitidas:
        return False, "invalid_transition"

    return True, ""


def transicionar(convocatoria, estado_destino: str, *, actor, motivo: str = "") -> None:
    """Execute a state transition on a Convocatory.

    Args:
        convocatoria: Convocatory instance
        estado_destino: Target state
        actor: User performing the transition
        motivo: Reason for transition (required for CANCELADA)

    Raises:
        ValidationError: If transition is not allowed
    """
    estado_origen = convocatoria.estado

    # Validate transition
    es_valida, error_code = validar_transicion(estado_origen, estado_destino)

    if not es_valida:
        raise ValidationError({
            "estado": f"Transición inválida: {estado_origen} → {estado_destino} ({error_code})"
        })

    # Special validation for CANCELADA
    if estado_destino == Estado.CANCELADA:
        if not motivo:
            raise ValidationError({
                "motivo": "El motivo es requerido para cancelar una convocatoria"
            })

    # Execute transition
    convocatoria.estado = estado_destino
    convocatoria.save(update_fields=["estado"])


def get_transiciones_disponibles(estado_actual: str) -> set:
    """Get available transitions from current state.

    Args:
        estado_actual: Current state

    Returns:
        Set of valid destination states
    """
    return TRANSICIONES_PERMITIDAS.get(estado_actual, set())


def is_terminal(estado: str) -> bool:
    """Check if state is terminal (no further transitions)."""
    return estado in Estado.TERMINAL_STATES


def is_active(estado: str) -> bool:
    """Check if state is active (can be cancelled)."""
    return estado in Estado.ACTIVE_STATES
