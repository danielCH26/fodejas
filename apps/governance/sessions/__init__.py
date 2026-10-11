"""Sessions of the Junta and Comité Técnico (CHG-501 / CAP-017).

This package implements session lifecycle management:
  - Convocation with working-day notice validation (ORDINARIA ≥5 WD,
    EXTRAORDINARIA ≥2 WD — project.md §6.1.1).
  - Attendance registration and quorum guard (mitad + 1 of voting
    members; cargo-exempt members never count).
  - Agenda (Orden del Día) and one-person-one-vote voting.
  - Minutes (ActaSesion) with PDF + SHA-256 + electronic signature
    (CAP-029).

Refer to ``openspec/changes/CHG-501-sessions/proposal.md`` for the
full specification.
"""

from apps.governance.sessions import (
    models,  # noqa: F401
    services,  # noqa: F401
)
from apps.governance.sessions.models import (  # noqa: F401
    ActaSesion,
    MiembroSesion,
    OrdenDelDiaPunto,
    Sesion,
    Voto,
)
