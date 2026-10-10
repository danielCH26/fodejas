# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

#### CHG-303: Autorización de Desembolsos (CAP-010)

**Description**: Payment authorization with dual signatures and manual
Treasury reconciliation on top of the CHG-802 sweeps.

**Changes:**

- Dual-signature enforcement in `TreasuryService.authorize`
  (Presidente JA + Secretario de Educación; self-signing prevented in
  both directions).
- 4-normative-attachments guard in `send_to_treasury`
  (`REQUIRED_ATTACHMENT_TYPES`; 4th type assumed ACTO_ADMINISTRATIVO —
  governance integration pending).
- Guard: legalization process must be LEGALIZADO before authorizing;
  amount > 0 and immutable after authorization.
- List/detail/authorize HTMX views with role gating; admin registration.
- 64 tests (46 service + 18 views), including the VENCIDO 5-day sweep.

#### CHG-302: Legalización del Crédito (CAP-009)

**Description**: Credit legalization flow: per-beneficiary document
creation, PDF generation, completion and cancellation.

**Changes:**

- `LegalizationService`: `create_documents_for_beneficiary`,
  `generate_pdf` (WeasyPrint behind a renderer seam),
  `complete_legalization`, `cancel_document`.
- Domain FSM `apps/legalization/domain/transitions.py`
  (PENDIENTE → FIRMADO → LEGALIZADO / CANCELADO, terminal guards).
- Spanish legal PDF templates (pagaré, carta de instrucciones,
  contrato) + shared `legal.css`.
- Role-gated process list/detail views, R-JUNTA menu entry, admin
  filters; post-sign tamper detection test.
- 80 tests.

#### CHG-301: Firma Electrónica (CAP-029)

**Description**: Abstract electronic signature service with
interchangeable providers and SHA-256 hash storage.

**Changes:**

- `sign_legal_document` service (idempotent, deterministic signers,
  audit events from the service layer, pre/post hash verification).
- DRF API `sign`/`verify` + HTMX signing views + admin +
  `check_signer_config` management command (aborts mock provider
  outside development).
- 41 tests, including `test_e2e_create_sign_verify_audit_flow`.

#### Estabilización de la suite de tests

**Description**: Full suite green: 419 passed / 8 skipped / 0 failed.

**Changes:**

- Root cause of the 34 cascade teardown errors fixed: audit actor
  contextvar leaked across tests; autouse fixture resets it at test
  boundaries (`abdc9c4`).
- MD5 password hasher for test runs (treasury app 117s → 10s).
- ruff auto-fixes applied (1,440 issues); exposed and repaired two
  latent NameError bugs (silent audit-log failure in applications
  wizard; crash in claims `iniciar_revision`).
- 35 ruff items accepted as documented debt (E402/C901/B017).

#### CHG-112: Asignación de Roles a Usuarios

**Description**: Implemented role assignment functionality with Django auth integration.

**Changes:**

- **Models** (`apps/accounts/models.py`):
  - Added `group` OneToOneField to Role model (links to auth.Group)
  - Added `auth_permission` OneToOneField to Permission model (links to auth.Permission)

- **Services** (`apps/accounts/services/`):
  - Created `sync.py` with `sync_role_to_group()` and `sync_permission_to_auth_perm()`
  - Created `assignment.py` with `assign_role_to_user()` and `revoke_role_from_user()`
  - Created `permissions.py` with `get_user_effective_permissions()` and cache functions

- **Management Commands** (`apps/accounts/management/commands/`):
  - Created `sync_roles.py` to sync roles/permissions with Django auth

- **Views** (`apps/accounts/views/admin_views.py`):
  - Updated UserRoleAssignView to use assign_role_to_user() service
  - Updated UserRoleRevokeView to use revoke_role_from_user() service
  - Added UserRoleHistoryView for role change history

- **URLs** (`apps/accounts/admin_urls.py`):
  - Created new URL patterns for user role management

- **Templates** (`templates/accounts/admin/`):
  - Created admin_base.html
  - Created users/detail.html
  - Created users/roles.html
  - Created users/role_history.html

**Migrations:**
- `0004_role_group.py` - Adds group field to Role
- `0005_permission_auth_permission.py` - Adds auth_permission field to Permission

**Breaking Changes:**
- None

**Deprecations:**
- None

**Known Issues:**
- None

---

#### CHG-801: Reparar cadena de auditoría CAP-022

**Description**: Audit chain made transactional (select_for_update), silent try/except removed, actor contextvar wired via middleware.

**Changes:**
- **Services** (`apps/audit/services.py`):
  - `log_audit_event()` now wraps head-of-chain read + insert in `transaction.atomic` with `select_for_update()` — concurrent writers serialize correctly.
- **Signals** (`apps/audit/signals.py`):
  - `AUDIT_MODELS` keyed on model classes (not strings); receivers use `is`-equality; `get_actor()` from contextvar; silent `try/except` replaced by structured `logger.exception()`.
  - `register_audit_signals()` called from `AuditConfig.ready()`.
- **Middleware** (`apps/core/middleware.py`, `apps/core/logging_config.py`):
  - `actor_var: ContextVar` added; `RequestIDMiddleware` calls `set_actor(request.user)` on entry and `reset_actor()` on exit.
- **Replacements** (`apps/legalization/signer.py`, `apps/accounts/services/notifications.py`, `apps/convocatories/services/convocatoria_service.py`, `apps/applications/services/wizard_service.py`):
  - All direct `AuditEvent.objects.create()` calls replaced by `log_audit_event(...)` — zero remaining.
- **Permissions** (`apps/audit/views.py`):
  - `AuditEventListView` / `AuditEventDetailView` now require `IsAuditViewer` (not just `IsAuthenticated`).

**Tests** (`apps/audit/tests/`):
- `test_chain.py` — 3-event chain hash linkage verified.
- `test_concurrency.py` — 2-thread concurrent writes serialize; chain remains valid.
- `test_signals.py` — `Role` save fires audit event with correct actor.
- `test_views_permissions.py` — R-ASPIRANTE receives HTTP 403.

---

#### CHG-802: Celery + barridos de plazos (Tesorería 5 días, exoneración 30 días, habeas data 30 días)

**Description**: Celery infrastructure wired; sweep and alert tasks implemented for all three deadline enforcement windows.

**Changes:**
- **Celery** (`config/celery.py`, `config/__init__.py`):
  - `Celery` app with autodiscover; exported as `celery_app` from config.
- **Treasury** (`apps/treasury/models.py`, `apps/treasury/services.py`, `apps/treasury/tasks.py`):
  - Added `treasury_received_at` field and `VENCIDO` status to `DisbursementAuthorization`.
  - `TreasuryService` mutations wrapped in `@transaction.atomic` + `select_for_update()`.
  - `tesoreria_sweep_v5d` and `tesoreria_alert_v5d` shared tasks — idempotent, consult audit log before transitioning.
  - `TreasuryReconciliationView` (CBV, R-TESORERO) with payment-proof upload.
- **Condonation** (`apps/condonation/models.py`, `apps/condonation/tasks.py`):
  - Added `fecha_limite` field and `VENCIDO` status to `Sanction`.
  - `exoneracion_sweep_v30d` and `exoneracion_alert_v30d` — idempotent.
  - `SanctionService.submit_justification()` sets `fecha_limite = now + 30 days`.
- **Habeas Data** (`apps/accounts/models.py`, `apps/accounts/tasks.py`):
  - `SolicitudHabeasData.save()` auto-computes `fecha_limite` (30 working days) when omitted.
  - `habeas_sweep_v30d` and `habeas_alert_v30d` — idempotent.

**Tests** (`apps/treasury/tests/`, `apps/condonation/tests/`, `apps/accounts/tests/`):
- `test_sweep_v5d.py`, `test_sweep_v30d.py`, `test_habeas_sweep.py` — overdue transitions verified.
- `test_service_concurrency.py` — 2-thread authorize: one wins, other raises `ValueError`.
- `test_views_reconciliation.py` — R-TESORERO can POST payment proof.
- `test_justification_deadline.py` — `submit_justification` stamps `fecha_limite`.

---

#### CHG-803: Cabeceras de seguridad + WSGI de producción + límites de upload

**Description**: Production security hardening: HTTPS/HSTS/cookies, CORS, upload size limits, gunicorn WSGI entrypoint.

**Changes:**
- **Settings** (`config/settings.py`):
  - `IS_PRODUCTION` guard activates: `SECURE_SSL_REDIRECT`, HSTS family (1 year), `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`, `X_FRAME_OPTIONS = DENY`, `CORS_ALLOWED_ORIGINS` (official domains only), `CORS_ALLOW_CREDENTIALS`.
  - `DATA_UPLOAD_MAX_MEMORY_SIZE` and `FILE_UPLOAD_MAX_MEMORY_SIZE` set to 10 MB globally.
- **CORS** (`config/settings.py`):
  - `corsheaders` in `INSTALLED_APPS`; `CorsMiddleware` after `SecurityMiddleware`.
- **Container** (`docker/Dockerfile`):
  - `CMD` switched from `runserver` to `gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60`.
- **Dependencies** (`pyproject.toml`):
  - Added `gunicorn>=21.2`, `django-cors-headers>=4.3`.
- **Docs** (`.env.production.example`):
  - Documented `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `ALLOWED_HOSTS`.

**Tests** (`config/tests/`):
- `test_settings_prod.py` — verifies security settings with `DJANGO_ENV=production`.
- `test_upload_limits.py` — 11 MB POST returns HTTP 400.

---

#### CHG-804: Seguridad de migraciones (expand/contract + backfill UUID en PKs)

**Description**: UUID backfill migrations, expand/contract migration guide, and CI guard preventing unsafe PK alterations.

**Changes:**
- **Migrations** (`apps/accounts/migrations/0008_backfill_uuids_customuser_role.py`, `apps/convocatories/migrations/0003_backfill_uuids_convocatory.py`):
  - Data-only `RunPython` migrations: detect UUID PKs (noop if already UUID), otherwise reassign PKs with `uuid.uuid5(NAMESPACE_URL, "app:model:{old_pk}")`.
  - `reverse_code` documented as noop — forward-only by design.
- **Docs** (`docs/migrations/expand-contract.md`):
  - 4-step recipe (expand → backfill → swap → contract), migration template, destructive-history table, revert guide.
- **CI** (`.github/workflows/migrations-safety.yml`):
  - Runs on PR and push to main/develop. Checks `makemigrations --check --dry-run` and heuristic scan for unsafe `AlterField + primary_key=True` without a backfill migration.

**Tests** (`apps/accounts/tests/test_migrations_uuid.py`, `apps/convocatories/tests/test_migrations_uuid.py`):
- Idempotency when PK is already UUID.
- Forward and reverse migrations leave DB consistent.

---

#### CHG-805: Defectos de dominio (listado, scoring, RBAC, apelaciones, normativas)

**Description**: Fixed critical domain bugs identified in extended audit.

**Changes:**
- **Listado** (`apps/governance/services/listado.py`):
  - Replaced stale `Convocatory.Estado.RESULTADOS_DEFINITIVOS` with `DEFINITIVA`.
  - Replaced `puntaje_merito` → `puntaje_excelencia`; `puntaje_residencia` removed; `puntaje_academico` added to payload.
  - Silent `try/except` replaced by `try/except AttributeError` with structured log.
- **Scoring** (`apps/scoring/services/scoring_service.py`):
  - `calcular_puntaje_total` wrapped in `@transaction.atomic`; `PuntajeTotal.objects.select_for_update().get_or_create()`.
- **RBAC dedup** (`apps/accounts/permissions.py`):
  - Duplicate `class HasRole` removed; kept the one with `__init__(role_code)`.
  - `has_revisor_role` in `apps/applications/views.py` and `has_comite_role` / `RankingView` in `apps/scoring/views.py` delegate to `has_role()`.
- **Appeal import** (`apps/claims/permissions.py`):
  - `CanCreateApelacion` now imports `validar_apelacion` (not stale `can_apelar`).
- **Normativa** (`apps/convocatories/models.py`):
  - Placeholder `"Art. ..."` literals replaced with `# TENTATIVE-CITATION` comments and concrete article numbers (`Art. 11 Decreto 0372/2025`, `Art. 2 Decreto 0072/2026`, `Art. 17 Decreto 0372/2025`).

**Tests** (`apps/governance/tests/test_listado_definitivo.py`, `apps/scoring/tests/test_scoring_atomic.py`, `apps/accounts/tests/test_permissions_unique_hasrole.py`, `apps/claims/tests/test_appeal_permission.py`, `apps/convocatories/tests/test_normativa_catalog.py`):
- All new test files created; no entry in `NORMATIVA` catalog has a literal placeholder article.

---

#### CHG-806: Limpieza de stubs y placeholder de junta sessions

**Description**: Removed stub apps (reporting, psychosocial) from INSTALLED_APPS and codebase; created governance sessions placeholder.

**Changes:**
- **Removed** (`config/settings.py`):
  - Removed `"apps.reporting"` and `"apps.psychosocial"` from `INSTALLED_APPS`.
- **Deleted**:
  - `apps/reporting/` directory and all files.
  - `apps/psychosocial/` directory and all files.
- **Created** (`apps/governance/sessions/`):
  - `__init__.py` with CAP-017 docstring.
  - `README.md` documenting deferred implementation (CHG-501-sessions, Fase 5).
- **Docs** (`docs/stubs-removed.md`):
  - Table of removed apps with their CAP-NNN references; justification; reintroduction guide.

**Tests** (`apps/tests/test_stubs_removed.py`):
- `test_reporting_directory_does_not_exist`, `test_psychosocial_directory_does_not_exist` — directories absent.
- `test_governance_sessions_package_exists`, `test_governance_sessions_has_readme` — placeholder present.
- `test_settings_installed_apps_excludes_stubs` — stub apps absent from settings.
- `test_stubs_removed_doc_exists` — `docs/stubs-removed.md` present.

---

## [2026-07-02]

### Previous Changes

See git history for details.
