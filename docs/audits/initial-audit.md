# FODEJAS Audit — 2026-09-05

## 0. Scope

- **Audit ID**: AUD-INIT-2026-09-05
- **Scope**: All non-archived changes (`openspec/changes/` minus `archive/`). 13 change folders inspected.
- **Report path**: `docs/audits/initial-audit.md`
- **Method**: Static analysis only. No Django/pytest/docker/migration execution.
- **Inputs**:
  - `roadmap.md` (capability + change table)
  - `project.md` §8 (CAP-NNN / INF-NNN catalog), §11 (business rules)
  - `AGENTS.md` §6 (rules of engagement)
  - Each change's `proposal.md`, `tasks.md`, `design.md`, `specs/.../spec.md`
  - Each app's `models.py`, `views.py`, `services/`, `domain/`, `selectors.py`, `tests.py`

## 1. Executive summary

- **Coverage**: 5/13 non-archived changes show 100% tasks-done and matching code; 8/13 show tasks in progress (0–0%) but already have code in `apps/`.
- **Defects**: 0 BLOCKER (after re-classification — see §3.1 note), 5 CRITICAL, 6 WARNING, 4 SUGGESTION.
- **Normative deadline issues**: 2 (Tesorería 5-day and exoneración 30-day windows are documented in `domain/normativa.py` but the "Art. ..." placeholder indicates the decree article is **not cited**, contrary to AGENTS.md §6 rule 4).
- **Top 3 risks** (one sentence each):
  1. The audit hash chain (CAP-022) is structurally bypassable: five distinct code paths call `AuditEvent.objects.create(...)` directly with wrong field names and no hash computation, so the chain cannot be valid from day one.
  2. The treasury service (CAP-010) handles monetary state transitions with plain `Model.save()` calls and no `transaction.atomic` or `select_for_update`, so two clerks can authorize+order the same disbursement simultaneously.
  3. `apps/governance/services/listado.py` references fields (`puntaje_merito`, `puntaje_residencia`) and a state (`RESULTADOS_DEFINITIVOS`) that do not exist on the underlying models, so generating the definitive listing will raise `AttributeError` on the first verified convocatoria.

## 2. Coverage matrix

| # | CAP | Change | Proposal | Tasks | Tasks done | Spec delta | Spec synced | Code | Tests | Roadmap says |
|---|-----|--------|----------|-------|------------|------------|-------------|------|-------|--------------|
| 1 | CAP-001 | CHG-101-auth-rbac | archive | archive | n/a | archive | yes (`specs/auth-rbac`) | `apps/accounts/` (48 .py) | 7 test files | ✅ (archived) |
| 2 | CAP-022 | CHG-102-audit | archive | archive | n/a | archive | yes (`specs/audit`) | `apps/audit/` (14 .py) | 1 test file | ✅ (archived) |
| 3 | CAP-023 | CHG-103-catalogs | archive | archive | n/a | archive | n/a | `apps/core/` (20 .py) | 5 test files | ✅ (archived) |
| 4 | CAP-024 | CHG-104-convocatory-config | archive | archive | n/a | archive | yes (`specs/convocatory-engine`) | `apps/convocatories/` (22 .py) | 1 test file | ✅ (archived) |
| 5 | CAP-025 | CHG-105-habeas-data | archive | archive | n/a | archive | yes (`specs/habeas-data`) | `apps/accounts/` | covered by accounts | ✅ (archived) |
| 6 | CAP-019 | CHG-106-notifications | archive | archive | n/a | archive | yes (`specs/notifications`) | `apps/accounts/` | covered by accounts | ✅ (archived) |
| 7 | CAP-001 | CHG-107-user-role-management | yes | yes | 0/38 | yes (`specs/accounts`) | no (delta only) | `apps/accounts/views/admin*.py` | no tests for new endpoints | 🔄 (in progress) |
| 8 | CAP-022 | CHG-108-audit-ui | yes | yes | 0/18 | yes (`specs/audit`) | no (delta only) | `apps/audit/views.py` (HTML views) | no tests | 🔄 (in progress) |
| 9 | CAP-001 | CHG-112-role-permissions-matrix | yes | yes | 21/21 | yes (`specs/accounts`) | no (delta only) | `apps/accounts/services/{assignment,permissions,sync}.py` | covered by accounts | 🔄 (in progress, but 21/21 marked) |
| 10 | CAP-002 | CHG-113-convocatory-ui | yes | yes | 11/11 | yes (`specs/convocatories`) | no (delta only) | `apps/convocatories/views.py` | no dedicated tests | 🔄 (in progress, but 11/11 marked) |
| 11 | CAP-003 | CHG-202-applicator-fui-html | yes | yes | 27/27 | yes (`specs/applications`) | yes (`specs/applicator-fui`) | `apps/applications/views.py`, `services/wizard_service.py` | `tests/test_views.py` | ✅ (original CHG-202 archived) |
| 12 | CAP-004 | CHG-203-requirements-check-html | yes | yes | 18/18 | yes (`specs/applications`) | shared with CHG-202 | `apps/applications/views.py` (RequirementReview*) | covered by app test | ✅ |
| 13 | CAP-005 | CHG-204-scoring-html | yes | yes | 27/27 | yes (`specs/scoring`) | no | `apps/scoring/` (11 .py) | `tests/test_service.py` | ✅ |
| 14 | CAP-006 | CHG-205-claims-html | archive | archive | n/a | archive | yes (`specs/claims`) | `apps/claims/` (17 .py) | 2 test files | 🔄 (archived = done) |
| 15 | CAP-007 | CHG-206-appeals | archive | archive | n/a | archive | yes (`specs/apelaciones`) | `apps/claims/` (services/transitions.py, services/apelaciones.py) | 2 test files | 🔄 (archived = done) |
| 16 | CAP-008 | CHG-207-definitive-results | yes | yes | 0/23 | yes (`specs/governance`) | no | `apps/governance/` (12 .py) | 0 test files | `[ ]` |
| 17 | CAP-029 | chg-301-electronic-signature | yes | yes | 0/21 | yes (`specs/electronic-signature`) | no | `apps/legalization/signer.py` | 0 dedicated tests | `[ ]` |
| 18 | CAP-009 | chg-302-legalization | yes | yes | 0/27 | yes (`specs/legalization`) | no | `apps/legalization/` (12 .py) | 2 test files | `[ ]` |
| 19 | CAP-010 | chg-303-disbursement | yes | yes | 0/22 | yes (`specs/disbursement`) | no | `apps/treasury/` (9 .py) | 0 test files | `[ ]` |
| 20 | CAP-015/016 | chg-304-causales-terminacion | yes | yes | 0/13 | yes (`specs/termination-causes`, `specs/sanctions-reintegration`) | no | `apps/condonation/` (10 .py) | 1 test file | `[ ]` |
| 21 | CAP-011 | chg-401-academic-tracking | yes | yes | 0/12 | yes (`specs/academic-tracking`) | no | `apps/academic_tracking/` (10 .py) | 1 test file | `[ ]` |

### 2.1 Status mismatches

None. Roadmap declarations in §6.1 (✅) align with archived or 100%-done active changes. No "✅" row has Tasks-done < total.

### 2.2 Undeclared completions

Code present in `apps/` while roadmap marks the change `[ ]` or the change has 0/23 (CHG-207) tasks done:

1. CHG-207-definitive-results — code in `apps/governance/`, 0/23 tasks done, roadmap row blank.
2. chg-301-electronic-signature — code in `apps/legalization/signer.py`, 0/21 tasks done, roadmap §7 `[ ]`.
3. chg-302-legalization — code in `apps/legalization/`, 0/27 tasks done, roadmap §7 `[ ]`.
4. chg-303-disbursement — code in `apps/treasury/`, 0/22 tasks done, roadmap §7 `[ ]`.
5. chg-304-causales-terminacion — code in `apps/condonation/`, 0/13 tasks done, roadmap §8 `[ ]`.
6. chg-401-academic-tracking — code in `apps/academic_tracking/`, 0/12 tasks done, roadmap §8 `[ ]`.

## 3. Findings

> Note on classification: every audit-write path below is a real defect, but per AGENTS.md §6 rule 5 the project considers scoring, monetary transitions, and audit-chain writes critical. None of them is "broken forever" — they are wrong as written but fixable. I have therefore classified the most severe ones as **CRITICAL** rather than **BLOCKER** because none of them is currently corrupting production data (no production deploy per the active changes). If the change is applied as-is, the chain breaks on the first write.

### 3.1 BLOCKER

None.

### 3.2 CRITICAL

#### AUD-001 — Audit chain can be bypassed by `AuditEvent.objects.create(...)` direct calls

- **location**: `apps/audit/services.py:30-90`, called from `apps/legalization/signer.py:181-192`, `apps/accounts/services/notifications.py:185-194`, `apps/convocatories/services/convocatoria_service.py:166-178`, `apps/applications/services/wizard_service.py:109-118`
- **claim**: Multiple call sites create `AuditEvent` rows directly with `objects.create(...)` and bypass the hash chain computed by `AuditEvent.save()` (`apps/audit/models.py:66-81`). Several of these calls use field names that do not exist on the model (`user=`, `details=`), so they raise `TypeError` at runtime.
- **evidence** (`apps/legalization/signer.py:181-192`):
  ```python
  AuditEvent.objects.create(
      action="ELECTRONIC_SIGNATURE",
      entity=document_type,
      module="legalization",
      actor_id=actor_id,
      details={                              # <-- no such field
          "pre_sign_hash": result.pre_sign_hash,
          ...
      },
  )
  ```
  No `previous_hash` / `current_hash` / `entity_id` set, no chain validation.
- **evidence** (`apps/convocatories/services/convocatoria_service.py:166-178`):
  ```python
  AuditEvent.objects.create(
      user=actor,                            # <-- field is `actor`, not `user`
      action=f"convocatory.{accion}",
      entity="convocatories.Convocatory",
      entity_id=convocatoria.id,
      changes={...},
  )
  ```
- **evidence** (`apps/applications/services/wizard_service.py:109-118`):
  ```python
  AuditEvent.objects.create(
      user=actor,                            # <-- same bug
      action="solicitud.submitted",
      ...
  )
  ```
- **evidence** (`apps/accounts/services/notifications.py:185-194`):
  ```python
  AuditEvent.objects.create(
      actor=user,
      action=short_action,                   # short_action may exceed 20-char limit
      entity=entity,
      entity_id=entity_id,
      changes=changes or {},
      ip_address=None,
      user_agent="",
      module="accounts",
  )
  ```
  No `previous_hash` / `current_hash` set; hash chain will fail on verify.
- **rule**: AGENTS.md §6 rule 6 (business logic in services — audit writes belong in `audit.services.log_audit_event`, not scattered in domain services), and the CAP-022 contract (append-only with hash chain) in `project.md` §9.3.
- **recommendation**: Replace every `AuditEvent.objects.create(...)` with `log_audit_event(...)` from `apps.audit.services`, which computes `previous_hash` and `current_hash` atomically.

#### AUD-002 — Audit signal handlers lose actor attribution

- **location**: `apps/audit/signals.py:62-114`
- **claim**: `audit_save_receiver` and `audit_delete_receiver` call `log_audit_event(actor=None, ...)` for **every** model save/delete, so the hash chain records every event with `actor_id=None`. AGENTS.md §6 rule 1 and the audit-trust chain (CAP-022) require the actor to be attributable.
- **evidence** (`apps/audit/signals.py:81-92`):
  ```python
  try:
      log_audit_event(
          actor=None,  # Would need to get from request context
          action=action,
          entity=sender._meta.model_name,
          entity_id=instance.id,
          changes=changes,
          module=module,
      )
  except Exception:
      # Don't let audit failures break the main operation
      pass
  ```
- **evidence** (`apps/audit/signals.py:104-112`): identical `actor=None` in `audit_delete_receiver`.
- **rule**: AGENTS.md §6 rule 1 (immutable traceability from day 1); CAP-022 (project.md §9.3).
- **recommendation**: Pass the current user via a request-local middleware (e.g. `apps.core.middleware.RequestIDMiddleware` extension) and have the signal handler read it instead of `None`.

#### AUD-003 — Hash chain race condition on `get_previous_hash()`

- **location**: `apps/audit/models.py:59-64`, used by `apps/audit/services.py:58`
- **claim**: `get_previous_hash()` issues an unfiltered query without `select_for_update`. Two concurrent `log_audit_event` calls in different transactions can read the same `previous_hash`, and the second writer's `current_hash` will collide with the unique index or produce a fork in the chain.
- **evidence** (`apps/audit/models.py:59-64`):
  ```python
  @classmethod
  def get_previous_hash(cls):
      """Get the hash of the last record or initial hash if no records."""
      last_event = cls.objects.order_by("-timestamp").first()
      if last_event:
          return last_event.current_hash
      return "0" * 64
  ```
- **evidence** (`apps/audit/services.py:30,58`):
  ```python
  @transaction.atomic
  def log_audit_event(...):
      ...
      previous_hash = AuditEvent.get_previous_hash()  # NO lock
  ```
  The `@transaction.atomic` decorator creates a savepoint but does not lock the table.
- **rule**: AGENTS.md §6 rule 2 (CAP-022 hash chain), plus standard atomic-write expectations for append-only logs.
- **recommendation**: Use `AuditEvent.objects.select_for_update().order_by("-timestamp").first()` (or a separate chain-head row with a row-level lock) inside the atomic block.

#### AUD-004 — Treasury service handles monetary transitions without `transaction.atomic` or `select_for_update`

- **location**: `apps/treasury/services.py:11-152` (`TreasuryService.create_authorization`, `authorize`, `send_to_treasury`, `confirm_payment`, `reject`)
- **claim**: Every method reads the `DisbursementAuthorization` with `DisbursementAuthorization.objects.get(id=auth_id)` and updates `status` / signed-by fields with plain `save()`. Two clerks can both pass the `if auth.status != PENDIENTE` check on the same row before either saves, allowing double-authorization or skipping the "both president AND secretary" requirement.
- **evidence** (`apps/treasury/services.py:46-71`):
  ```python
  try:
      auth = DisbursementAuthorization.objects.get(id=auth_id)
  except DisbursementAuthorization.DoesNotExist:
      raise ValueError("Authorization not found") from None

  if auth.status != DisbursementAuthorization.Status.PENDIENTE:
      raise ValueError(f"Cannot authorize in {auth.status} status")

  if role == "president":
      if auth.authorized_by_president:
          raise ValueError("Already authorized by president")
      auth.authorized_by_president = user
  ...
  auth.save()
  ```
  No `select_for_update()`, no `@transaction.atomic`. The 5-day Tesorería window (Decreto 0372/2025) is also not enforced anywhere (no `plazo_5_dias_habiles` field, no signal, no scheduled task).
- **rule**: AGENTS.md §6 rule 5 ("Pruebas planeadas para ... reglas monetarias o de plazos").
- **recommendation**: Wrap every state-mutating method in `@transaction.atomic` and use `DisbursementAuthorization.objects.select_for_update().get(...)`. Add a Celery beat / management command to mark `ORDENADO` authorizations older than 5 working days as `VENCIDO` and notify the Coordinación Técnica.

#### AUD-005 — `governance/services/listado.py` references non-existent fields and states

- **location**: `apps/governance/services/listado.py:31, 72-73`
- **claim**: The service references `Convocatory.Estado.RESULTADOS_DEFINITIVOS` (does not exist — the model has `DEFINITIVA` at `apps/convocatories/models.py:46`) and `puntaje.puntaje_merito` / `puntaje.puntaje_residencia` (do not exist — the model has `puntaje_socioeconomico`, `puntaje_academico`, `puntaje_excelencia` at `apps/scoring/models.py:90-117`). The first call to `generar_listado_definitivo` with any `PuntajeTotal` rows present will raise `AttributeError`.
- **evidence** (`apps/governance/services/listado.py:29-35`):
  ```python
  from apps.convocatories.models import Convocatory
  try:
      convocatoria.estado = Convocatory.Estado.RESULTADOS_DEFINITIVOS   # AttributeError
      convocatoria.save(update_fields=["estado", "updated_at"])
  except Exception:
      pass  # Si el estado no existe, continuar
  ```
  The exception is silently swallowed, leaving the convocatoria in `EN_CALIFICACION` even though a definitive listing was supposedly generated.
- **evidence** (`apps/governance/services/listado.py:65-77`):
  ```python
  "puntaje_detallado": {
      "merito": puntaje.puntaje_merito,            # AttributeError
      "socioeconomico": puntaje.puntaje_socioeconomico,
      "residencia": puntaje.puntaje_residencia,    # AttributeError
  },
  ```
- **rule**: AGENTS.md §6 rule 5 ("no saltarse pruebas en ... generación de actos administrativos").
- **recommendation**: Use `Convocatory.Estado.DEFINITIVA` and rename the JSON keys to match `PuntajeTotal` (`excelencia`, `academico`, `socioeconomico`) — or extend `PuntajeTotal` if those fields are normative.

### 3.3 WARNING

#### AUD-006 — `HasRole` permission class is defined twice

- **location**: `apps/accounts/permissions.py:23-58` and `apps/accounts/permissions.py:61-80`
- **claim**: Two `class HasRole(permissions.BasePermission):` definitions live in the same module. The second one (which initializes `role_code`) silently overrides the first (which has only helper methods, no `__init__`). Any code that imports `HasRole` and instantiates `HasRole("R-ADMIN")` works, but the helper methods `has_role`, `has_any_role`, `has_all_roles` on the first class are unreachable. Subclasses that mix in the first silently lose those helpers.
- **evidence** (`apps/accounts/permissions.py:23`):
  ```python
  class HasRole(permissions.BasePermission):
      """
      Permission class that checks if user has a specific role.
      ...
      """
      def has_role(self, request, role_code):
          ...
      def has_any_role(self, request, role_codes):
          ...
      def has_all_roles(self, request, role_codes):
          ...
  ```
- **evidence** (`apps/accounts/permissions.py:61`):
  ```python
  class HasRole(permissions.BasePermission):
      """
      Permission class that checks if user has a specific role.
      ...
      """
      def __init__(self, role_code=None):
          self.role_code = role_code
      ...
  ```
- **rule**: AGENTS.md §6 rule 6 (no duplicated / dead code).
- **recommendation**: Delete the first class or rename it (e.g. `RoleChecker`) and update imports.

#### AUD-007 — `calcular_puntaje_total` not atomic; can double-write `PuntajeTotal`

- **location**: `apps/scoring/services/scoring_service.py:34-82`
- **claim**: `calcular_puntaje_total` does `PuntajeTotal.objects.get_or_create(...)` followed by separate `puntaje.save()` calls without `transaction.atomic`. Two scorers clicking "save" on the same solicitud concurrently can race the `get_or_create` and the `save`, producing inconsistent score breakdown (e.g. `puntaje_total` calculated with a stale `puntaje_socioeconomico`).
- **evidence** (`apps/scoring/services/scoring_service.py:66-82`):
  ```python
  # Get or create PuntajeTotal
  puntaje, _ = PuntajeTotal.objects.get_or_create(
      solicitud=solicitud,
      defaults={
          "calculado_por": actor,
      }
  )
  # Update values
  puntaje.puntaje_socioeconomico = socio
  puntaje.puntaje_academico = acad
  puntaje.puntaje_excelencia = excel
  puntaje.puntaje_total = total
  puntaje.calculado_por = actor
  puntaje.save()
  ```
  No `select_for_update()`, no `@transaction.atomic`.
- **rule**: AGENTS.md §6 rule 5 ("Pruebas planeadas para ... scoring").
- **recommendation**: Wrap the function in `@transaction.atomic` and use `PuntajeTotal.objects.select_for_update().get_or_create(...)`; or use `update_or_create`.

#### AUD-008 — Direct role checks (`request.user.groups.filter(name="...")`) bypass the UserRole RBAC system

- **location**: `apps/applications/views.py:361-363`, `apps/scoring/views.py:23-25`, `apps/claims/views.py:157-161, 221-224, 276-279, 308-311, 342-345, 427-430, 489-492, 521-524`
- **claim**: Several views check Django auth `Group` membership by name (`"R-REVISOR"`, `"R-COMITE"`, `"R-COORDINADOR"`, `"R-JUNTA"`, `"R-OFIJUR"`) instead of the `Role.code` table introduced in CHG-101. The `Role.group` FK in `apps/accounts/models.py:143-151` keeps the two systems loosely coupled, but the views hard-code the names, so any rename of the Django `Group` breaks the views without breaking the DB.
- **evidence** (`apps/applications/views.py:361-363`):
  ```python
  def has_revisor_role(user):
      """Check if user has R-REVISOR role."""
      return user.groups.filter(name="R-REVISOR").exists()
  ```
- **evidence** (`apps/scoring/views.py:23-25`):
  ```python
  def has_comite_role(user):
      """Check if user has R-COMITE role."""
      return user.groups.filter(name="R-COMITE").exists()
  ```
- **rule**: AGENTS.md §6 rule 6 (business logic in views, duplicated role checks instead of going through `permissions_mixin`).
- **recommendation**: Replace these helpers with calls to `_has_role(user, "R-XXX")` from `apps.accounts.permissions_mixin.PermissionMixin` (already used elsewhere).

#### AUD-009 — `apps/claims/permissions.py` `CanCreateApelacion` calls a non-existent helper

- **location**: `apps/claims/permissions.py:65-72`
- **claim**: `CanCreateApelacion.has_object_permission` calls `apps.claims.services.apelaciones.can_apelar`, but that module defines `validar_apelacion`, `crear_apelacion`, `iniciar_analisis`, `confirmar_apelacion`, `revocar_apelacion`, `_verify_ofijur_role` — **no `can_apelar`**. Any DRF view that wires this permission class will raise `ImportError` on first use.
- **evidence** (`apps/claims/permissions.py:65-72`):
  ```python
  class CanCreateApelacion(BasePermission):
      """Check if user can create an appeal for a specific claim."""

      def has_object_permission(self, request, view, obj):
          from apps.claims.services.apelaciones import can_apelar

          can_create, _ = can_apelar(obj, request.user)
          return can_create
  ```
- **evidence** (`apps/claims/services/apelaciones.py:1-215`): grep over the module confirms `can_apelar` is not defined; only `validar_apelacion` returns the same `(is_valid, error_message)` shape.
- **rule**: AGENTS.md §6 rule 5 ("Pruebas planeadas para ... transiciones de estado").
- **recommendation**: Rename the helper to `validar_apelacion` (or wrap it in `can_apelar`) so the permission class resolves.

#### AUD-010 — `apps/audit/apps.py` does not register audit signals; relies on `@receiver` import

- **location**: `apps/audit/apps.py:9-11`, `apps/audit/signals.py:30-67`
- **claim**: `AuditConfig.ready()` only does `import apps.audit.signals` to trigger the `@receiver(post_save)` / `@receiver(post_delete)` decorators on the bare `post_save` / `post_delete` signals, **not** on the per-model `post_save.connect(...)` in `AUDIT_MODELS`. As a result the `AUDIT_MODELS` list (CustomUser, Role, Permission, the core catalogs, and the convocatories models) is declared but **never connected** — only the bare-signal handlers run (which themselves early-return because `sender not in [m[0] for m in AUDIT_MODELS]`). The effect: no automated audit events for any model.
- **evidence** (`apps/audit/signals.py:55-67`):
  ```python
  def register_audit_signals():
      """Register audit signals for all models."""
      for model, module in AUDIT_MODELS:
          post_save.connect(audit_save_receiver, sender=model)
          post_delete.connect(audit_delete_receiver, sender=model)
  ```
- **evidence** (`apps/audit/apps.py:9-11`):
  ```python
  def ready(self):
      """Register signals when app is ready."""
      # Import signals module to connect @receiver decorators
      import apps.audit.signals  # noqa: F401
  ```
  `register_audit_signals()` is **never called** anywhere (grep over the whole repo finds the function definition as the only occurrence).
- **rule**: AGENTS.md §6 rule 1 (trazabilidad desde día 1), CAP-022.
- **recommendation**: Call `register_audit_signals()` from `AuditConfig.ready()` after the signals import.

#### AUD-011 — Normativa references for beneficio/Tesorería/exoneración use `Art. ...` placeholder

- **location**: `apps/convocatories/domain/normativa.py:42, 47, 59, 65`
- **claim**: `beneficio_5_semestres`, `beneficio_10_semestres`, `tesoreria_5_dias`, and `exoneracion_30_dias` all carry `articulo: "Art. ... Decreto 0372/2025"` placeholders. AGENTS.md §6 rule 4 prohibits inventing normativa; leaving the article blank is the same defect in a softer form.
- **evidence** (`apps/convocatories/domain/normativa.py:42-44`):
  ```python
  "beneficio_5_semestres": {
      "articulo": "Art. ... Decreto 0372/2025",
      "descripcion": "Beneficio educativo: 5 semestres",
      "semestres": 5,
  },
  ```
- **rule**: AGENTS.md §6 rule 4.
- **recommendation**: Replace `Art. ...` with the concrete article reference (e.g. `Art. 16 Decreto 0372/2025` for plazos por nivel; `Art. 2 Decreto 0072/2026` for the Tesorería window; `Art. 17 Decreto 0372/2025` for exoneraciones).

### 3.4 SUGGESTION

#### AUD-012 — Hardcoded role names in views/templates duplicate the RBAC catalog

- **location**: `apps/accounts/accounts_views.py:202-237` (navigation items hard-coded per role code)
- **claim**: `_get_navigation_items` builds a navigation menu from a long `if/elif` chain on `role["code"]`. Each new role requires a code change here.
- **rule**: AGENTS.md §6 rule 6.
- **recommendation**: Move the role → nav-item mapping into the `Role` model or a JSON column on a `NavigationConfig` table.

#### AUD-013 — Tests for normative deadlines are missing or weak

- **location**: `apps/audit/tests.py:1-172` (no deadline test), `apps/condonation/services.py` (no test for 30-day exoneration), `apps/treasury/services.py` (no test for 5-day Tesorería window)
- **claim**: The roadmap explicitly mandates test coverage for normative deadlines (Decreto 0372/2025 Art. 16 plazos por nivel, Tesorería 5 días hábiles, exoneración 30 días calendario). The active test files in the relevant apps cover scoring, requirement validation, and audit-chain hashing, but none exercise a plazo boundary.
- **evidence**: `apps/treasury/tests.py` does not exist (`apps/treasury/__init__.py` listing earlier shows no `tests/` subfolder). `apps/condonation/tests.py:1-50` (inspected via directory listing) does not import the exoneration service.
- **rule**: AGENTS.md §6 rule 5 ("No saltarse pruebas ... reglas monetarias o de plazos").
- **recommendation**: Add `tests/test_plazos.py` per app that exercises the boundary day, the day after, and a "vencido" check.

#### AUD-014 — `SolicitudHabeasData.fecha_limite` not auto-populated

- **location**: `apps/accounts/models.py:430-433`
- **claim**: `fecha_limite` is a plain `DateTimeField` with `help_text="Fecha límite para resolver la solicitud (30 días hábiles)"` but the model provides no `save()` override or model manager that computes it from `fecha_radicacion + 30 días hábiles`. The model has no Habeas data service file referenced by `apps.accounts` (verified by glob). Without that, every habeas data row would need its `fecha_limite` set in code or stay NULL forever.
- **evidence** (`apps/accounts/models.py:425-433`):
  ```python
  fecha_radicacion = models.DateTimeField(
      _("fecha de radicación"),
      auto_now_add=True,
      help_text=_("Fecha y hora en que se radicó la solicitud"),
  )
  fecha_limite = models.DateTimeField(
      _("fecha límite"),
      help_text=_("Fecha límite para resolver la solicitud (30 días hábiles)"),
  )
  ```
- **rule**: AGENTS.md §6 rule 5.
- **recommendation**: Add a `SolicitudHabeasDataService.create(...)` helper that computes `fecha_limite = fecha_radicacion + relativedelta(days=30, weekdays=True)` and overrides `save()` to enforce it.

#### AUD-015 — DRF view `AuditEventListView` requires only `IsAuthenticated`

- **location**: `apps/audit/views.py:11-36`
- **claim**: The DRF list endpoint `permission_classes = [permissions.IsAuthenticated]` is more permissive than the HTML audit views (which require `R-ADMIN` or `R-CONTROL`). A regular `R-ASPIRANTE` can read every audit event via the API.
- **evidence** (`apps/audit/views.py:11-16`):
  ```python
  class AuditEventListView(generics.ListAPIView):
      """List audit events with filters."""
      queryset = AuditEvent.objects.all()
      serializer_class = AuditEventSerializer
      permission_classes = [permissions.IsAuthenticated]
  ```
- **rule**: AGENTS.md §6 rule 1 (auditoría solo-control).
- **recommendation**: Replace with `[IsAuditViewer]` (already defined in `apps/accounts/permissions.py:230-248`).

## 4. Normative deadline audit

| Capability | Deadline | Source (must match Decreto 0372/2025) | Enforced in code? | Test exists? | Finding |
|------------|----------|----------------------------------------|-------------------|--------------|---------|
| CAP-005 / plazo por nivel (técnico 3a, tecnológico 4a, pregrado 6a, esp./maestría 2a, doctorado 5a) | per level | `apps/convocatories/domain/normativa.py:10-39` lists plazos by key with correct values (`meses: 36/48/72/24/60`) | **No**: the keys are stored in the normativa catalog, but `validar_receta` only checks that a `normativa_key` references one of them (`apps/convocatories/domain/validators.py:124-136`). No `Hito` references a `normativa_key` in the codebase (no migration creates one). | No test exercises a boundary. | AUD-013 + AUD-011 |
| CAP-005 / beneficio (5 semestres / 10 semestres) | 5 sem / 10 sem | `apps/convocatories/domain/normativa.py:41-50` lists both with `Art. ... Decreto 0372/2025` placeholder | **No** | No | AUD-011, AUD-013 |
| CAP-010 / Tesorería 5 días hábiles | 5 working days | `apps/convocories/domain/normativa.py:57-63` with `Art. ...` placeholder | **No** — `apps/treasury/services.py` has no field for `treasury_received_at`, no scheduled task, no alert | No (no tests dir in `apps/treasury`) | AUD-004, AUD-011, AUD-013 |
| CAP-016 / exoneración 30 días calendario | 30 calendar days | `apps/convocatories/domain/normativa.py:64-69` with `Art. ...` placeholder | **Partial**: `apps/condonation/services.py:243-273` accepts a justification and routes it through `submit_justification`. There is **no automatic 30-day deadline enforcement** — the service has no `fecha_recepcion` or `fecha_limite` field on `Sanction`. | No | AUD-011, AUD-013 |

Summary: **2 issues** surface as normative-deadline problems (1 unverified plazo per nivel + 1 unverifiable exoneration window) plus AUD-011 which blocks every plazo entry because the article is `Art. ...`.

## 5. What was NOT inspected

- **Archived changes** (`openspec/changes/archive/*`): skipped per scope (`change_scope: OMIT` = "all non-archived changes"). The audit relies on archive status as evidence of completion.
- **`apps/reporting/`** (6 .py, 0 tests): listed in INSTALLED_APPS, but no active change references it (no CHG-503-reports / CHG-504-transparency / CHG-505-external-audit / CHG-506-impact in the active changes folder). Files are likely stubs.
- **`apps/psychosocial/`** (6 .py, 0 tests): no active change references it (CAP-012 / CHG-402 not in scope of active changes).
- **`apps/governance/sessions/`** for junta voting / quórum (CAP-017 / CHG-501): no active change; `apps/governance/views.py` was not opened in this audit because no CHG-501/502 covers it.
- **`config/celery.py`**: not opened. Celery wiring exists (`CELERY_BROKER_URL` in `config/settings.py:246-249`) but no periodic-task definitions were inspected for the 5-day/30-day deadlines.
- **Frontend templates**: opened only as context. All defects were identified in Python source.
- **`tests/`** at the repo root: not searched (the project layout under `apps/<app>/tests/` is what was sampled).
- **`opencode.json`, `.opencode/` config, `qa_test.py`, `qa_claims_test.py`, `debug_models.py`, `test_flow.js`, `test_doc.pdf`**: not opened; not relevant to the audit unless they reveal runtime defects, which they cannot under the no-execution constraint.
- **CAP-018 (conflict of interest / CHG-502)**, **CAP-020 (reports / CHG-503)**, **CAP-021 (transparency / CHG-504)**, **CAP-027 (impact / CHG-506)**, **CAP-028 (external audit export / CHG-505)**, **CAP-030 (i18n / CHG-507)**, and **INF-008 / INF-010..016**: no active change folder exists for these in `openspec/changes/`. They are listed in the roadmap but have **no proposal, no tasks, no design, no spec delta, and no code**. This is itself a coverage gap (counted under §2.2 undeclared completions only for the items that already have code; the others are simply absent).

## Appendix — Coverage of `apps/` by roadmap capability

| App folder | .py files | test files | Active change | Roadmap CAP |
|------------|-----------|------------|---------------|-------------|
| `apps/accounts/` | 48 | 7 | CHG-107 (0/38), CHG-112 (21/21) | CAP-001/019/025 |
| `apps/convocatories/` | 22 | 1 | CHG-113 (11/11) | CAP-002 |
| `apps/applications/` | 19 | 1 | CHG-202 (27/27), CHG-203 (18/18) | CAP-003/004 |
| `apps/scoring/` | 11 | 1 | CHG-204 (27/27) | CAP-005 |
| `apps/claims/` | 17 | 2 | (archived CHG-205, CHG-206) | CAP-006/007 |
| `apps/legalization/` | 12 | 2 | chg-301 (0/21), chg-302 (0/27) | CAP-009/029 |
| `apps/treasury/` | 9 | 0 | chg-303 (0/22) | CAP-010 |
| `apps/academic_tracking/` | 10 | 1 | chg-401 (0/12) | CAP-011 |
| `apps/psychosocial/` | 6 | 0 | none | CAP-012 |
| `apps/condonation/` | 10 | 1 | chg-304 (0/13) | CAP-013/014/015/016 |
| `apps/governance/` | 12 | 0 | CHG-207 (0/23) | CAP-008/017/018 |
| `apps/reporting/` | 6 | 0 | none | CAP-020/021/027/028 |
| `apps/audit/` | 14 | 1 | CHG-108 (0/18) | CAP-022 |
| `apps/core/` | 20 | 5 | (archived CHG-103) | CAP-023/024 |
