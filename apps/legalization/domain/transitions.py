"""State machine transitions for LegalDocument (CHG-302, CAP-009).

Implements the FSM defined in design.md D3:
  PENDIENTE → FIRMADO → LEGALIZADO
                  ↓
             CANCELADO

Every transition is validated before execution.  Post-sign hash
tamper detection lives in the service layer, not here.
"""
from apps.legalization.models import LegalDocument, LegalizationProcess

# -------------------------------------------------------------------
# Document-level transitions  (LegalDocument.Status)
# -------------------------------------------------------------------

# PENDIENTE documents can be signed or cancelled.
DOC_TRANSITIONS = {
    LegalDocument.Status.PENDIENTE: {
        LegalDocument.Status.FIRMADO,
        LegalDocument.Status.CANCELADO,
    },
    # FIRMADO documents can advance to LEGALIZADO or be cancelled.
    LegalDocument.Status.FIRMADO: {
        LegalDocument.Status.LEGALIZADO,
        LegalDocument.Status.CANCELADO,
    },
    # Terminal: LEGALIZADO and CANCELADO accept no transitions.
    LegalDocument.Status.LEGALIZADO: set(),
    LegalDocument.Status.CANCELADO: set(),
}

# -------------------------------------------------------------------
# Process-level transitions  (LegalizationProcess.Status)
# -------------------------------------------------------------------

PROCESS_TRANSITIONS = {
    LegalizationProcess.Status.PENDIENTE: {
        LegalizationProcess.Status.EN_PROCESO,
        LegalizationProcess.Status.CANCELADO,
    },
    LegalizationProcess.Status.EN_PROCESO: {
        LegalizationProcess.Status.LEGALIZADO,
        LegalizationProcess.Status.CANCELADO,
    },
    # Terminal.
    LegalizationProcess.Status.LEGALIZADO: set(),
    LegalizationProcess.Status.CANCELADO: set(),
}


def get_valid_document_transitions(current_status: str) -> set:
    """Return allowed target states for a LegalDocument in *current_status*."""
    return DOC_TRANSITIONS.get(current_status, set())


def get_valid_process_transitions(current_status: str) -> set:
    """Return allowed target states for a LegalizationProcess in *current_status*."""
    return PROCESS_TRANSITIONS.get(current_status, set())


def is_valid_document_transition(current: str, target: str) -> bool:
    """Return True when current → target is a permitted LegalDocument transition."""
    return target in get_valid_document_transitions(current)


def is_valid_process_transition(current: str, target: str) -> bool:
    """Return True when current → target is a permitted LegalizationProcess transition."""
    return target in get_valid_process_transitions(current)


def is_document_terminal(status: str) -> bool:
    """Return True when *status* has no outgoing transitions."""
    return status in (
        LegalDocument.Status.LEGALIZADO,
        LegalDocument.Status.CANCELADO,
    )


def is_process_terminal(status: str) -> bool:
    """Return True when *status* has no outgoing transitions."""
    return status in (
        LegalizationProcess.Status.LEGALIZADO,
        LegalizationProcess.Status.CANCELADO,
    )
