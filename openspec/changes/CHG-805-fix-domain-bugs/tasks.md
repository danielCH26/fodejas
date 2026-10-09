# Tasks — CHG-805 — Defectos de dominio (listado, scoring, RBAC, apelaciones, normativa)

## 1. AUD-005 — `governance/services/listado.py` field/state references

- [x] Replace `Convocatory.Estado.RESULTADOS_DEFINITIVOS` with `Convocatory.Estado.DEFINITIVA`.
- [x] Replace `puntaje.puntaje_merito` → `puntaje.puntaje_excelencia`, drop `puntaje.puntaje_residencia`, keep `puntaje.puntaje_socioeconomico` and add `puntaje.puntaje_academico` to the `puntaje_detallado` payload.
- [x] Replace the silent `try/except Exception: pass` with a `try/except AttributeError` that logs at WARNING and emits a structured event so the convocatoria state transition failure is not swallowed.

## 2. AUD-007 (CRITICAL) — scoring atomic + `select_for_update`

- [x] Wrap `calcular_puntaje_total` in `@transaction.atomic`.
- [x] Replace the bare `PuntajeTotal.objects.get_or_create(...)` with `PuntajeTotal.objects.select_for_update().get_or_create(solicitud=solicitud, defaults={"calculado_por": actor})`.
- [x] Confirm `evaluaciones` reads inside the function do not need additional locking (read-only, no race).

## 3. AUD-006 — `HasRole` dedup in `accounts/permissions.py`

- [x] Confirm (via grep) that no call site invokes `HasRole(...).has_role(...)` / `.has_any_role(...)` / `.has_all_roles(...)`.
- [x] Delete the first `class HasRole(permissions.BasePermission):` (helpers-only). Keep the second one (with `__init__(role_code)`).
- [x] The module-level helpers `has_role`, `has_any_role`, `get_user_roles`, etc. already exist further down the file and are the documented public surface — no extraction needed.

## 4. AUD-008 — replace direct `groups.filter(name=...)` checks

- [x] `apps/applications/views.py:361-363` — `has_revisor_role(user)` delegates to the `Role` table via the module-level helper `has_role(user, "R-REVISOR")` from `apps.accounts.permissions`.
- [x] `apps/scoring/views.py:23-25` — `has_comite_role(user)` delegates to `has_role(user, "R-COMITE")`.
- [x] `apps/scoring/views.py:158` — `RankingView.dispatch()` replaces `request.user.groups.filter(name="R-COORDINADOR").exists()` with `has_role(request.user, "R-COORDINADOR")`.
- [x] Leave `apps/claims/views.py` alone (already uses `Role.objects.filter(code=...).filter(...).exists()` per the audit).

## 5. AUD-009 — `CanCreateApelacion` imports

- [x] `apps/claims/permissions.py:69-71` — replace `from apps.claims.services.apelaciones import can_apelar` with `from apps.claims.services.apelaciones import validar_apelacion`.
- [x] Replace `can_create, _ = can_apelar(obj, request.user)` with `can_create, _ = validar_apelacion(obj, request.user)` (signature-compatible per `apps/claims/services/apelaciones.py:6-43`).

## 6. AUD-011 — replace `Art. ...` placeholders in `normativa.py`

- [x] `beneficio_5_semestres` and `beneficio_10_semestres` → `articulo: "Art. 11 Decreto 0372/2025"` with `# TENTATIVE-CITATION` comment.
- [x] `tesoreria_5_dias` → `articulo: "Art. 2 Decreto 0072/2026"` (treasury window is per audit §4, separate decree) with `# TENTATIVE-CITATION` comment.
- [x] `exoneracion_30_dias` → `articulo: "Art. 17 Decreto 0372/2025"` (sanction exoneration per audit §3.4) with `# TENTATIVE-CITATION` comment.
- [x] Sweep for any other `"Art. ..."` literal in the file; if found, replace analogously.

## 7. Tests

- [x] `apps/governance/tests/test_listado_definitivo.py` (NEW): `generar_listado_definitivo` does not raise and transitions to `DEFINITIVA`.
- [x] `apps/scoring/tests/test_scoring_atomic.py` (NEW): two concurrent `calcular_puntaje_total` calls produce a consistent `PuntajeTotal` (gated by `pytest.mark.skipif` on SQLite / non-Postgres).
- [x] `apps/accounts/tests/test_permissions_unique_hasrole.py` (NEW): only one `class HasRole` in the module; `HasRole(role_code=...)` accepts the kwarg.
- [x] `apps/claims/tests/test_appeal_permission.py` (NEW): `CanCreateApelacion.has_object_permission(...)` does not raise `ImportError`.
- [x] `apps/convocatories/tests/test_normativa_catalog.py` (NEW): no entry in `NORMATIVA` has `articulo == "Art. ... ..."` (literal placeholder sweep).

## 8. Hand-off

- [x] Write `openspec/changes/CHG-805-fix-domain-bugs/apply-progress.md` summarizing what changed, what was verified, and any blockers / follow-ups.
- [x] Run `python -c "import ast; [ast.parse(open(p).read()) for p in [...]]"` for all touched Python files to confirm syntactic validity.
- [x] Run `pytest` over the new test files (best-effort) and record pass/fail honestly. Do not amend history.

## Verification

- [x] `openspec/changes/CHG-805-fix-domain-bugs/specs/scoring/spec.md` written.
- [x] `openspec/changes/CHG-805-fix-domain-bugs/specs/governance/spec.md` written.
- [x] `openspec/changes/CHG-805-fix-domain-bugs/specs/accounts/spec.md` written.
- [x] `openspec/changes/CHG-805-fix-domain-bugs/specs/claims/spec.md` written.
- [x] `openspec/changes/CHG-805-fix-domain-bugs/specs/convocatory-engine/spec.md` written.

## Out of scope

- Audit log chain fix → CHG-801.
- Treasury Celery 5-day-window enforcement → CHG-802.
- Security headers → CHG-803.
- Migration hygiene → CHG-804.
- Caching of repeated `_has_role` calls per request → later change if benchmarks demand it.
- Wholesale rename of `validar_apelacion` → `can_apelar` → later change if the helper semantics diverge.
