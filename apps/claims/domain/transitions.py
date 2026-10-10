"""State transitions for claims (CHG-205) and appeals (CHG-206)."""

from apps.claims.models import Apelacion, Reclamacion

# Transition matrix: estado_actual -> [estados_validos]
TRANSITIONS = {
    Reclamacion.Estado.PRESENTADA: [
        Reclamacion.Estado.EN_REVISION,
        Reclamacion.Estado.RECHAZADA,  # Por vencimiento
    ],
    Reclamacion.Estado.EN_REVISION: [
        Reclamacion.Estado.RESUELTA,
        Reclamacion.Estado.RECHAZADA,
    ],
    Reclamacion.Estado.RESUELTA: [],
    Reclamacion.Estado.RECHAZADA: [],
}

# Transition matrix for appeals
APELACION_TRANSITIONS = {
    Apelacion.Estado.PRESENTADA: [
        Apelacion.Estado.EN_ANALISIS,
    ],
    Apelacion.Estado.EN_ANALISIS: [
        Apelacion.Estado.CONFIRMADA,
        Apelacion.Estado.REVOCADA,
    ],
    Apelacion.Estado.CONFIRMADA: [],
    Apelacion.Estado.REVOCADA: [],
}


def get_valid_transitions(estado_actual):
    """Get valid target states from current state."""
    return TRANSITIONS.get(estado_actual, [])


def is_valid_transition(estado_actual, nuevo_estado):
    """Check if transition is valid."""
    return nuevo_estado in get_valid_transitions(estado_actual)


def can_transition_to(estado_actual, *target_states):
    """Check if current state can transition to any of target states."""
    valid = get_valid_transitions(estado_actual)
    return any(t in valid for t in target_states)


def get_transition_label(estado_actual, nuevo_estado):
    """Get human-readable transition label."""
    labels = {
        (Reclamacion.Estado.PRESENTADA, Reclamacion.Estado.EN_REVISION): "Iniciar revisión",
        (Reclamacion.Estado.EN_REVISION, Reclamacion.Estado.RESUELTA): "Aceptar reclamación",
        (Reclamacion.Estado.EN_REVISION, Reclamacion.Estado.RECHAZADA): "Rechazar reclamación",
        (Reclamacion.Estado.PRESENTADA, Reclamacion.Estado.RECHAZADA): "Vencimiento",
        (Apelacion.Estado.PRESENTADA, Apelacion.Estado.EN_ANALISIS): "Iniciar análisis",
        (Apelacion.Estado.EN_ANALISIS, Apelacion.Estado.CONFIRMADA): "Confirmar apelación",
        (Apelacion.Estado.EN_ANALISIS, Apelacion.Estado.REVOCADA): "Revocar apelación",
    }
    return labels.get((estado_actual, nuevo_estado), f"{estado_actual} → {nuevo_estado}")


def get_valid_apelacion_transitions(estado_actual):
    """Get valid target states for appeals from current state."""
    return APELACION_TRANSITIONS.get(estado_actual, [])


def is_valid_apelacion_transition(estado_actual, nuevo_estado):
    """Check if appeal transition is valid."""
    return nuevo_estado in get_valid_apelacion_transitions(estado_actual)


def can_apelacion_transition_to(estado_actual, *target_states):
    """Check if current appeal state can transition to any of target states."""
    valid = get_valid_apelacion_transitions(estado_actual)
    return any(t in valid for t in target_states)
