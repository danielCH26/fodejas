# apply-progress — CHG-805 (FODEJAS domain bug fixes)

## Goal

Implement the six findings flagged in `docs/audits/initial-audit.md` and
`docs/audits/extended-audit.md`:

- AUD-005 — `governance/services/listado.py` referenced non-existent
  fields and a non-existent `Convocatory.Estado`.
- AUD-006 — `HasRole` permission class was declared twice in
  `apps/accounts/permissions.py`.
- AUD-007 (reclassified **CRITICAL**) — `calcular_puntaje_total` was
  not atomic and not locked at the row level.
- AUD-008 — three views bypassed the `Role` table and queried Django's
  `Group` directly by name.
- AUD-009 — `CanCreateApelacion` imported a non-existent helper.
- AUD-011 — four `NORMATIVA` entries carried placeholder article
  references.

## Spec deltas (5 capabilities)

- `openspec/changes/CHG-805-fix-domain-bugs/specs/scoring/spec.md` — AUD-007.
- `openspec/changes/CHG-805-fix-domain-bugs/specs/governance/spec.md` — AUD-005.
- `openspec/changes/CHG-805-fix-domain-bugs/specs/accounts/spec.md` — AUD-006 + AUD-008.
- `openspec/changes/CHG-805-fix-domain-bugs/specs/claims/spec.md` — AUD-009.
- `openspec/changes/CHG-805-fix-domain-bugs/specs/convocatory-engine/spec.md` — AUD-011.

## Code changes

| File | Lines changed | Note |
|------|---------------:|------|
| `apps/governance/services/listado.py` | 1–36, 56–92 | AUD-005: `DEFINITIVA`, real `PuntajeTotal` field names, explicit `try/except (AttributeError, ValueError)` with WARNING log instead of bare `except Exception: pass`. |
| `apps/scoring/services/scoring_service.py` | 34–84 | AUD-007 CRITICAL: `@transaction.atomic` decorator on `calcular_puntaje_total`; `PuntajeTotal.objects.select_for_update().get_or_create(...)` replacing the bare `get_or_create`. |
| `apps/accounts/permissions.py` | 17–37, 43–58 | AUD-006: deleted the duplicate `class HasRole` that only had helper instance methods. The remaining class (with `__init__(role_code=...)`) is unchanged; module-level helpers `has_role` / `has_any_role` continue to expose the same logic. |
| `apps/applications/views.py` | 358–365 | AUD-008: `has_revisor_role` routes through `apps.accounts.permissions.has_role(user, "R-REVISOR")`. |
| `apps/scoring/views.py` | 12, 23–27, 154–163 | AUD-008 (2 sites): `has_comite_role` and `RankingView.dispatch` go through the module-level `has_role` helper. |
| `apps/claims/permissions.py` | 65–78 | AUD-009: `from apps.claims.services.apelaciones import validar_apelacion` (was the non-existent `can_apelar`). |
| `apps/convocatories/domain/normativa.py` | 40–68 | AUD-011: four `Art. ... Decreto …` placeholders replaced with `Art. 11 Decreto 0372/2025` (beneficio 5/10 sem.), `Art. 2 Decreto 0072/2026` (Tesorería 5 días hábiles), `Art. 17 Decreto 0372/2025` (exoneración 30 días calendario). Each replacement carries a `# TENTATIVE-CITATION: confirmar con equipo legal antes de deploy a producción` comment so a single `grep` finds every entry pending legal confirmation. |

## Tests added

| Path | Status | Notes |
|------|--------|-------|
| `apps/governance/tests/test_listado_definitivo.py` | 3 passed | Asserts `generar_listado_definitivo` transitions to `DEFINITIVA` and that `obtener_ranking_final` reads the real `PuntajeTotal` field names (no `merito`/`residencia`). |
| `apps/scoring/tests/test_scoring_atomic.py` | 0 passed, 4 skipped | The scoring atomic tests skip on SQLite (the configured dev backend); they would run on PostgreSQL. The skip is encoded both via a runtime vendor check inside each test and via the module-level `pytest.mark.skipif` shown at the bottom of the file. |
| `apps/accounts/tests/test_permissions_unique_hasrole.py` | 5 passed | Asserts `HasRole` is defined exactly once, accepts `role_code=...`, is a DRF permission subclass, and that the module-level helpers still exist with the right signature. |
| `apps/claims/tests/test_appeal_permission.py` | 4 passed | Asserts `CanCreateApelacion` imports cleanly, exposes `has_object_permission`, source contains no functional reference to `can_apelar` (comments are stripped before the check), and that `validar_apelacion(obj, actor)` is the wired helper with the documented signature. |
| `apps/convocatories/tests/test_normativa_catalog.py` | 3 passed | Iterates `NORMATIVA` and rejects any entry whose `articulo` contains `Art. …`. Also asserts the four plazo entries declare a citation matching the expected decree. |

## Verification

- `python -c "import ast; [ast.parse(open(p).read()) for p in [...]]"` over the 12 modified files: `parse OK`.
- `python -m pytest apps/governance/tests/test_listado_definitivo.py apps/scoring/tests/test_scoring_atomic.py apps/accounts/tests/test_permissions_unique_hasrole.py apps/claims/tests/test_appeal_permission.py apps/convocatories/tests/test_normativa_catalog.py --no-header -q`: **15 passed, 4 skipped, 0 failed** on the configured SQLite dev backend. The 4 skipped tests are the scoring atomic ones, gated by both `pytest.mark.skipif` and a runtime vendor probe.

## Decisions / deviations

- AUD-008 routing: the proposal's spec says to use
  `PermissionMixin._has_role(user, "CODE")`. The three call sites in
  scope are: two module-level helpers (`has_revisor_role`,
  `has_comite_role`) plus one inline check in
  `RankingView.dispatch`. For the module-level helpers I used the
  sibling module-level `has_role(user, role_code)` from
  `apps.accounts.permissions` (functionally identical,
  `PermissionMixin._has_role` is just an instance-method wrapper
  around the same `user_roles.filter(role__code=…).exists()`
  query). The substantive intent — "no more
  `user.groups.filter(name='R-XXX')`" — is satisfied; the same
  `Role.code` lookup is the only source of truth. For
  `RankingView.dispatch`, I added the import on the same line as the
  existing one to keep the diff minimal.
- AUD-006 decision: I deleted the duplicate helper-only `HasRole`
  entirely. A grep across `apps/` confirmed no caller invoked the
  instance methods `has_role` / `has_any_role` / `has_all_roles` on
  the deleted class; every existing call site either uses
  module-level functions from `permissions.py` or instantiates the
  surviving class as `HasRole(role_code=...)`.
- AUD-011 citations: I marked every modified entry with
  `# TENTATIVE-CITATION: confirmar con equipo legal antes de deploy
  a producción`. The proposed `Art. 11` for `beneficio_*_semestres`,
  `Art. 2 Decreto 0072/2026` for `tesoreria_5_dias` and `Art. 17
  Decreto 0372/2025` for `exoneracion_30_dias` are the values from
  the audit's own recommendation; legal confirmation must close the
  loop before any production deploy.

## Out of scope (not touched)

- Audit log chain rework → CHG-801.
- Treasury Celery 5-day window enforcement → CHG-802.
- Security headers → CHG-803.
- Migration hygiene → CHG-804.
- Caching repeated `_has_role` calls per request (deferred).

## Follow-ups

- Open a tracking issue for legal confirmation of the four tentative
  citations in `apps/convocatories/domain/normativa.py`
  (`beneficio_5_semestres`, `beneficio_10_semestres`,
  `tesoreria_5_dias`, `exoneracion_30_dias`).
- Decide whether to refactor `RankingView` to inherit
  `CommitteePermissionMixin` (or a new `CoordinatorPermissionMixin`)
  so the inline role check in `dispatch` disappears.
- Decide whether to rename `validar_apelacion` → `can_apelar` as a
  follow-up cleanup, since the audit's eventual API expectation is
  the shorter name.

## Hand-off readiness

- [x] Tasks from `tasks.md` executed.
- [x] 5 spec deltas in place under `specs/`.
- [x] Code changes applied (12 files including new tests).
- [x] Pytest collection is green (15 passed, 4 skipped, 0 failed).
- [x] Working tree only — no commits made (per AGENTS.md §2 and the
  prompt's "NEVER commit changes").
