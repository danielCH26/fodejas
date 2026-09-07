# Spec Delta — `governance` (CAP-017 sessions placeholder)

> Delta para CHG-806. Bloques `## ADDED` según plantilla OpenSpec.

## ADDED

### Requirement: Marcador de sesiones de Junta (CAP-017, Fase 5)

`apps/governance/sessions/` **SHALL** existir como paquete Python
(presencia de `__init__.py` + `README.md`) desde el cierre de
CHG-806, **aún cuando** la implementación completa de CAP-017 quede
diferida a Fase 5 (`roadmap.md §9.1`).

El paquete **SHALL** contener únicamente:

- `__init__.py` — docstring que cita CAP-017, la fase pendiente, y el
  change OpenSpec que lo implementará (`CHG-501-sessions`).
- `README.md` — descripción del propósito, referencia a `roadmap.md`,
  y la estructura mínima esperada cuando se implemente
  (`models.py`, `services/quorum.py`, `services/voting.py`,
  `views/sesiones.py`).

El paquete **MUST NOT** contener otros archivos hasta que
`CHG-501-sessions` se apruebe. Cualquier archivo adicional debe
justificarse en una propuesta OpenSpec.

#### Scenario: Dev futuro intenta usar el módulo antes de CHG-501

- **WHEN** un developer hace `from apps.governance.sessions import X`,
- **THEN** el import falla con `ModuleNotFoundError` claro,
- **AND** el `README.md` indica que la funcionalidad es placeholder y
  redirige a CHG-501.
