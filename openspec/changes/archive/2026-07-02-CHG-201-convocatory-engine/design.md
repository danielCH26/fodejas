# Design: CHG-201-convocatory-engine — Motor de Ciclo de Estados de Convocatoria

## Technical Approach

Implement a **Finite State Machine (FSM)** for Convocatory state transitions using a pure domain layer (`domain/transitions.py`) that is fully testable without Django ORM. The service layer (`services/convocatoria_service.py`) orchestrates transitions with business rules, delegating validation to existing CHG-104 infrastructure.

## Architecture Decisions

| # | Decision | Choice | Alternatives | Rationale |
|---|----------|--------|--------------|----------|
| 1 | FSM representation | Pure Python class in `domain/transitions.py` | Django model + signals | Testable without DB; AGENTS.md §6.6 |
| 2 | State storage | Existing `Convocatory.estado` CharField | New related model | CHG-104 already has the field |
| 3 | Transition validation | Predicate functions returning (bool, error_code) | Exception-based | Enables detailed error reporting |
| 4 | Audit wiring | Extend `AuditEvent.action` to include transition events | Separate audit table | CHG-102 already tracks all CRUD |
| 5 | Notifications | Use CHG-106 InAppNotifier | Custom notification logic | Reuse existing infrastructure |

## Data Flow

```
Admin/API Request
       │
       ▼
domain/transitions.py::transicionar(convocatoria, nuevo_estado)
       │                              │
       │                              ├─> validate_transition() → ValidationError
       │                              ├─> validate_business_rules() → ValidationError
       │                              │
       ▼                              ▼
services/convocatoria_service.py::ejecutar_transicion()
       │
       ├──► Update Convocatory.estado
       ├──► AuditEvent (transition logged)
       ├──► Notification (if published/closed)
       └──► Return result
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `apps/convocatories/domain/__init__.py` | Modify | Export transition functions |
| `apps/convocatories/domain/transitions.py` | Create | Pure FSM class with transitions |
| `apps/convocatories/services/__init__.py` | Modify | Export service functions |
| `apps/convocatories/services/convocatoria_service.py` | Create | Transition orchestration |
| `apps/convocatories/api/serializers.py` | Create | Transition serializers |
| `apps/convocatories/api/views.py` | Create | Transition API endpoints |
| `apps/convocatories/admin.py` | Modify | Add transition actions |
| `apps/convocatories/urls.py` | Modify | Add transition routes |
| `apps/audit/signals.py` | Modify | Extend action choices if needed |

## State Machine Definition

```
States: BORRADOR → PUBLICADA → EN_INSCRIPCION → EN_VERIFICACION → EN_CALIFICACION → DEFINITIVA → CERRADA
         │           │
         │           └─► CANCELADA (from any active state)
         │
         └─► CANCELADA (from BORRADOR)

Valid transitions defined in TRANSICIONES_PERMITIDAS dict.
```

## Business Rules

1. **Publicar**: Requires `Convocatory.config` to exist (CHG-104)
2. **Cerrar**: Requires at least one DEFINITIVA result
3. **Cancelar**: Allowed from any non-terminal state (BORRADOR, PUBLICADA, EN_INSCRIPCION, EN_VERIFICACION, EN_CALIFICACION, DEFINITIVA)
4. All transitions logged to audit with action `convocatory.transition`

## Testing Strategy

| Layer | What | Approach |
|-------|------|---------|
| Unit | `transitions.py` pure functions | Mock-free testing with state dictionaries |
| Unit | Predicate validation logic | Table-driven tests |
| Service | Full transition workflow | `pytest-django` transactional |
| Integration | Admin bulk transitions | Selenium or API tests |
| Integration | API RBAC | DRF test client |

## Open Questions

- [ ] Should `EN_INSCRIPCION` automatically transition based on `fecha_cierre`? (Deferred to CAP-002 iteration)
- [ ] Public listing endpoint - CAP-021 scope? (Deferred)
