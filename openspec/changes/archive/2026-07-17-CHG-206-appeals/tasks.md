# Tasks: Apelaciones (2ª instancia)

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 550-650 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (Foundation) → PR 2 (Core Logic) → PR 3 (UI/Integration) |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Foundation setup | PR 1 | Base branch: develop; includes migration, model, basic tests |
| 2 | Core business logic | PR 2 | Base branch: PR 1; services, views, transitions |
| 3 | UI integration | PR 3 | Base branch: PR 2; templates, admin, final tests |

## Phase 1: Foundation / Infrastructure

- [x] 1.1 Create idempotent data migration for `R-OFIJUR` role in `apps/claims/migrations/0012_create_ofijur_role.py`
- [x] 1.2 Add `Apelacion` model to `apps/claims/models.py` with fields: `reclamacion` (FK to `Reclamacion`), `uuid` (UUIDField), `estado` (TextChoices), `resuelto_por`, `fecha_resolucion`, `respuesta`
- [x] 1.3 Implement `ApelacionHistorial` model for audit trail in `apps/claims/models.py`
- [x] 1.4 Write model tests in `apps/claims/tests.py` covering state transitions and validation rules

## Phase 2: Core Implementation

- [x] 2.1 Create `create_apelacion()` service in `apps/claims/services/apelaciones.py` validating: (a) reclamacion in terminal state, (b) within 30-day window, (c) user is titular
- [x] 2.2 Build state transition services (`iniciar_analisis()`, `confirmar()`, `revocar()`) in `apps/claims/services/apelaciones.py`
- [x] 2.3 Implement API views in `apps/claims/views.py`: `ApelacionCreateView`, `ApelacionTransitionView`, `ApelacionListView`, `ApelacionDetailView`, `ApelacionAdminListView`
- [x] 2.4 Configure URLs in `apps/claims/urls.py` for new endpoints
- [x] 2.5 Add permission classes in `apps/claims/views.py` for `R-ASPIRANTE` (create) and `R-OFIJUR` (transitions)

## Phase 3: Integration / Wiring

- [x] 3.1 Create templates in `templates/claims/apelacion_*.html` for listing and detail views
- [x] 3.2 Add `Apelacion` to Django admin in `apps/claims/admin.py`
- [x] 3.3 Implement UI wiring in `templates/claims/detail.html` to show apelacion link when applicable
- [x] 3.4 Add HTMX endpoints for state transitions in `apps/claims/views.py` (already included in transition views)

## Phase 4: Testing / Verification

- [x] 4.1 Write test `test_apelacion_creation_within_plazo()` in `test_views.py` validating 30-day window
- [x] 4.2 Create `test_transition_validation()` covering invalid actors/empty responses
- [x] 4.3 Add `test_historial_audit()` verifying audit trail entries
- [x] 4.4 Implement `test_visibility_permissions()` for titular vs OFIJUR access
- [x] 4.5 Verify integration with CAP-006 (Reclamaciones) via `test_reclamacion_integration()`

## Phase 5: Documentation / Cleanup

- [ ] 5.1 Update `docs/cap007-apelaciones.md` with new workflow diagrams
- [ ] 5.2 Add API documentation to `openapi.yaml` for new endpoints
- [ ] 5.3 Remove temporary debugging code from services