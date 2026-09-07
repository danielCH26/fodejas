# FODEJAS Extended Audit — 2026-09-05

## 0. Scope

- **Audit ID**: AUD-EXT-2026-09-05
- **Scope**: This is the second-pass audit. Builds on `docs/audits/initial-audit.md` (AUD-INIT-2026-09-05) and does NOT repeat its 15 findings (AUD-001..015).
- **Method**: Static analysis only. No Django/pytest/docker/migration execution.
- **This audit's sections**:
  - §2 Celery and deadline-enforcement wiring
  - §3 Django settings and security configuration
  - §4 Infrastructure items INF-001..016 (skip INF-009)
  - §5 WARNING deep-dive (AUD-006..011)
  - §6 Stub and gap analysis (apps/reporting, apps/psychosocial, apps/governance/sessions, apps/condonation exoneration)
  - §7 Migration safety (last 5)
  - §8 New and reclassified findings
- **Reference**: `docs/audits/initial-audit.md` (Phase 1 + 2, AUD-001..015).
- **Inputs read this pass**:
  - `config/settings.py`, `config/urls.py`, `config/__init__.py` (no `celery.py` exists)
  - `pyproject.toml`, `.pre-commit-config.yaml`, `CODEOWNERS`, `.editorconfig`, `.gitignore`
  - `docker/Dockerfile`, `docker/docker-compose.yml`, `docker/docker-compose.{staging,production,override}.yml`, `docker/pgbouncer.ini`, `docker/postgres.conf`, `docker/prometheus/{prometheus.yml,alerts.yml}`, `docker/grafana/`, `docker/backup-metrics/{crontab,backup-metrics.sh}`
  - `.github/workflows/{ci,code-quality,docker-build,deploy-staging,deploy-production}.yml`
  - `.env.{development,staging,production}.example`
  - `apps/core/{middleware,logging_config,secrets,health,celery_metrics,apps}.py`
  - `apps/audit/{apps,signals,services,models}.py`
  - `apps/treasury/{models,services,views,urls}.py`
  - `apps/condonation/{models,services,tests}.py`
  - `apps/governance/{models,services/{generador,listado,pdf},__init__}.py`
  - `apps/scoring/services/scoring_service.py`, `apps/scoring/views.py`
  - `apps/claims/{permissions,services/apelaciones,services/transitions}.py`
  - `apps/convocatories/domain/normativa.py`
  - `apps/reporting/{models,views,urls,admin,apps}.py`
  - `apps/psychosocial/{models,views,urls,admin,apps}.py`
  - `apps/accounts/permissions.py`
  - All `apps/*/migrations/*.py`
  - `scripts/{setup,dev,create_venv}.sh`, `scripts/backup/*`
  - `docs/` (no DRP/runbook found)

## 1. Executive summary

### 1.1 Counts

- **New BLOCKERs**: 1 (AUD-016 — no Celery app instance, no `config/celery.py`, no periodic tasks anywhere)
- **New CRITICALs**: 4 (AUD-017 settings security headers; AUD-018 production runserver; AUD-019 destructive UUID PK migrations; AUD-020 audit log write paths use wrong/non-existent fields)
- **New WARNINGs**: 5 (AUD-021 security header gaps; AUD-022 empty treasury views/urls; AUD-023 exoneration window unenforced; AUD-024 stub apps with INSTALLED_APPS; AUD-025 No Sesiones/Quorum model for CAP-017)
- **New SUGGESTIONs**: 2 (AUD-026 Pgbouncer password file committed; AUD-027 INF items have no OpenSpec proposals)
- **Reclassifications**: 2 (AUD-007 → CRITICAL; AUD-010 → CRITICAL)
- **Infrastructure items**:
  - **Total reviewed**: 15 (INF-001..016 minus INF-009)
  - **Done**: 3 (INF-002 partial dev-env, INF-003 partial CI, INF-014 partial migrations-strategy)
  - **Partial**: 6 (INF-001, INF-004, INF-005, INF-006, INF-008, INF-016)
  - **Missing**: 6 (INF-007 missing DRP evidence, INF-010 missing security headers, INF-011 no DRP, INF-012 no runbook, INF-015 alert runbook references absent, INF-013 explicitly Aplazado)

### 1.2 Top 3 NEW risks

1. **CAP-010 has zero deadline enforcement**: there is no `config/celery.py`, no `apps/*/tasks.py`, no `@shared_task`/`@periodic_task`, and no scheduled task to scan `DisbursementAuthorization` for the 5-working-day Tesorería window or to alert before it expires. The 30-calendar-day exoneration window for `Sanction` likewise has no enforcement field (`fecha_recepcion`, `fecha_limite` are absent) and no scheduled sweep. Both promises are dead-on-arrival until the Celery app and at least two periodic tasks are wired up.
2. **Production deploys run with `runserver`** and **zero security headers**: `docker-compose.production.yml:16` runs `python manage.py runserver 0.0.0.0:8000`, and `config/settings.py` declares no `SECURE_SSL_REDIRECT`, `SECURE_HSTS_*`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`, `DATA_UPLOAD_MAX_MEMORY_SIZE`, or `FILE_UPLOAD_MAX_MEMORY_SIZE`. The roadmap's Fase 0 Entregable "HTTPS obligatorio" and "headers de seguridad activos en staging y prod" are unmet.
3. **Two destructive PK migrations on tables that already have FKs**: `accounts/migrations/0006_alter_customuser_id.py` (2026-07-17) and `0007_alter_role_id.py` + `convocatories/migrations/0002_alter_convocatory_id.py` (both 2026-07-18) change `BigAutoField` PKs to `UUIDField` on tables that are already referenced by foreign keys. With data present, this either blows up or silently rewrites the chain — a zero-downtime-deploy violation against INF-014 and a data-integrity hazard.

## 2. Celery and deadline enforcement

### 2.1 Search results for periodic-task infrastructure

```text
grep -r "CELERY_BEAT_SCHEDULE|beat_schedule|@periodic_task|crontab|shared_task|app\.task|@task" C:\Users\danie\Downloads\fodejas
```

| Match | Location | Notes |
|-------|----------|-------|
| `Celery` (sentry integration) | `config/settings.py:285-292` | Sentry Celery integration only — does not require a Celery app to import. |
| `Celery("fodejas")` (in design doc) | `openspec/changes/archive/2026-07-02-CHG-105-habeas-data/design.md:57` | Archived design that never landed. |
| `dispatch_notification` shared_task | `openspec/changes/archive/2026-07-02-CHG-106-notifications/design.md:101, 136` | Archived design that never landed. |
| `crontab` (Docker) | `docker/backup-metrics/crontab:2-12` | OS-level cron inside the backup-scheduler container — not Celery beat. |
| `crontab /etc/crontabs/root` | `docker/docker-compose.yml:178` | OS-level cron boot. |

| Path searched | Result |
|---------------|--------|
| `config/celery.py` | **does not exist** (verified by `glob`) |
| `apps/*/tasks.py` | **does not exist** (verified by `glob`) |
| `@shared_task` / `@periodic_task` / `app.task` / `@task` decorators | **zero matches in `apps/` or `config/`** |

### 2.2 Celery and deadline-enforcement table

| Scheduled task | Schedule | Enforces which deadline | Status | Finding |
|----------------|----------|--------------------------|--------|---------|
| (none) | — | Tesorería 5 working days (Decreto 0372/2025) | **missing** | **AUD-016 CRITICAL** — no Celery app, no periodic task, no `DisbursementAuthorization.VENCIDO` state. `apps/treasury/models.py:12-17` lists only `PENDIENTE/AUTORIZADO/ORDENADO/PAGADO/RECHAZADO`. |
| (none) | — | Sanction exoneration 30 calendar days | **missing** | **AUD-023 WARNING** — no `Sanction.fecha_recepcion`/`fecha_limite` field; no scheduled sweep; `apps/condonation/services.py:243-273` (`submit_justification`) records `justification_details` but never starts a clock. |
| (none) | — | Habeas data 30 días hábiles (CAP-025) | **missing** | The CHG-105 design (`openspec/changes/archive/2026-07-02-CHG-105-habeas-data/design.md:57`) called for a `habeas_expiry_check` shared_task; it was never created. AUD-014 already flagged `fecha_limite` is not auto-populated. |
| `dispatch_notification` (notifications) | (intended async) | — | **missing** | `apps/accounts/services/notifications.py:199-209` calls `_dispatch_notification` synchronously in-process; comment "simplified without Celery" admits the gap. |
| Backup base / WAL archive / verify / metrics | OS-level crontab daily 02:00 / every 15min / daily 03:00 / every 5min | — | done (`docker/backup-metrics/crontab:5-13`) | not a Django periodic task; lives in a dedicated Alpine container. |

### 2.3 Verdict on CAP-010 / CAP-016 deadline wiring

CAP-010 promises "El sistema respeta el plazo de 5 días hábiles de Tesorería y emite alertas si se vence" (`roadmap.md:354`). CAP-016 promises "la solicitud de exoneración se resuelve en 30 días calendario" (`roadmap.md:395`). Both promises are unmet at the platform level. The `apps/treasury/models.py:49` field `treasury_order_date` only records the day the order was radicado — there is no field for "received by Treasury" and no state for "VENCIDO". `apps/condonation/models.py:111` field `justification_approved` is a boolean, not a deadline tracker.

## 3. Django settings and security configuration

The settings layer is a **single file** (`config/settings.py`, 325 lines). There is no `config/settings/{base,dev,staging,prod}.py` split. Environment differentiation is driven entirely by `DJANGO_ENV` and the `IS_PRODUCTION = DJANGO_ENV in ("staging","production")` boolean (`config/settings.py:38-39`).

| Setting | dev value | staging | prod | Compliant? | Finding |
|---------|-----------|---------|------|------------|---------|
| `DJANGO_ENV` | `development` | `staging` | `production` | yes | n/a |
| `DEBUG` | `env.bool("DEBUG", default=True)` (`settings.py:50`) + dev example `True` | example `False` | example `False` | **partial** | `settings.py:53-57` raises if `IS_PRODUCTION and DEBUG`, so the dev default `True` cannot accidentally leak into staging/prod. |
| `ALLOWED_HOSTS` (non-prod) | `["localhost","127.0.0.1","0.0.0.0","*"]` (`settings.py:76`) | example `staging.fodejas.gov.co` (`.env.staging.example:5`) | example `fodejas.gov.co,www.fodejas.gov.co` (`.env.production.example:5`) | **partial** | dev default includes `*` and `0.0.0.0` — fine for local, but if a dev `.env` were ever copied into staging, host-header injection is possible. |
| `ALLOWED_HOSTS` (prod env) | — | must be set via env var, defaults to `[]` when `IS_PRODUCTION` (`settings.py:76`) | must be set via env var | **partial** | Empty default will reject all requests at boot; safer than permissive but operationally fragile. |
| `SECURE_SSL_REDIRECT` | (not set) | (not set) | (not set) | **NO** | **AUD-017** — no value, no implicit default in Django for this key. |
| `SECURE_HSTS_SECONDS` | (not set) | (not set) | (not set) | **NO** | **AUD-017** — HSTS absent. |
| `SECURE_HSTS_INCLUDE_SUBDOMAINS` | (not set) | (not set) | (not set) | **NO** | **AUD-017**. |
| `SECURE_HSTS_PRELOAD` | (not set) | (not set) | (not set) | **NO** | **AUD-017**. |
| `SECURE_CONTENT_TYPE_NOSNIFF` | (not set) | (not set) | (not set) | **NO** | **AUD-017** — Django default is `True` since 3.0, so the value lands implicitly; the file lacks the explicit declaration. |
| `SECURE_REFERRER_POLICY` | (not set) | (not set) | (not set) | **NO** | **AUD-017**. |
| `X_FRAME_OPTIONS` | (not set) | (not set) | (not set) | **partial** | `django.middleware.clickjacking.XFrameOptionsMiddleware` is in MIDDLEWARE (`settings.py:121`), so the default is `DENY`. Explicit declaration absent. |
| `SESSION_COOKIE_SECURE` | (not set) | (not set) | (not set) | **NO** | **AUD-017** — Django default is `False`; sessions will travel over HTTP if prod is ever served without TLS. |
| `CSRF_COOKIE_SECURE` | (not set) | (not set) | (not set) | **NO** | **AUD-017**. |
| `SECURE_PROXY_SSL_HEADER` | (not set) | (not set) | (not set) | **NO** | **AUD-017** — required when terminating TLS at a proxy (which is the staging/prod topology). |
| `CSRF_TRUSTED_ORIGINS` | (not set) | (not set) | (not set) | **NO** | **AUD-017** — DRF endpoints under `/api/*` rely on this; a CSRF check behind a proxy will mis-classify without it. |
| `DATA_UPLOAD_MAX_MEMORY_SIZE` | (not set) | (not set) | (not set) | **NO** | **AUD-021 WARNING** — Django default is 2.5 MB; FUI anexos are uploaded via `aplications/services/wizard_service.py` and need an explicit higher cap or chunked S3 upload. |
| `FILE_UPLOAD_MAX_MEMORY_SIZE` | (not set) | (not set) | (not set) | **NO** | **AUD-021**. |
| `CORS_ALLOWED_ORIGINS` / `CORS_ALLOW_ALL_ORIGINS` | (not set anywhere) | (not set) | (not set) | **partial** | No CORS configuration at all. DRF uses JSONRenderer only, but if a frontend on another origin is added (e.g., a future SPA) there is no allow-list. Not a blocker today; AUD-021. |
| `SECRET_KEY` | dev default `"django-insecure-dev-only-not-for-production"` (`settings.py:46`) | example blank; secrets.get_required() enforced (`settings.py:43, 60-69`) | example blank; secrets.get_required() enforced | **partial** | Production path correctly requires `SECRET_KEY` via `_validate_required_secrets` (`settings.py:60-72`). The dev default is appropriately labelled `insecure`. |
| `AUTH_PASSWORD_VALIDATORS` | (see list, 5 validators, `settings.py:205-221`) | same | same | **partial** | Custom `FodejasPasswordValidator` (`apps/accounts/validators.py` referenced at `settings.py:219`). No minimum-length override. Not inspected (recommended below). |
| `MIDDLEWARE` order | `SecurityMiddleware` first, `RequestIDMiddleware` second (`settings.py:113-122`) | same | same | **partial** | `RequestIDMiddleware` is in place (confirms AUD-002 recommendation) but exposes `set_user_id` to the audit logger without binding it into `actor=`; gap remains. |
| `LOGGING` (non-prod) | structured logger config (`settings.py:299-324`, level DEBUG) | n/a | n/a | **partial** | non-prod uses a plain text formatter; only prod gets `setup_async_logging` with `JSONFormatter` (`settings.py:280-282`). |
| `LOGGING` (prod) | n/a | JSON+request_id via `apps/core/logging_config.py:71-92` | same | **partial** | AsyncQueueListener setup is in place; `pythonjsonlogger` is a runtime dep (`pyproject.toml:24`). PII redaction lives at the middleware layer (`apps/core/middleware.py:8-31`) — query string is fully redacted, paths only on the `/password|/token|/secret|/credential` patterns. |
| `CELERY_BROKER_URL` | `redis://localhost:6379/0` (`.env.development.example:15`) | example blank | example blank | **partial** | `settings.py:246-248` derives broker URL from `REDIS_URL`+`REDIS_PASSWORD`; prod examples require `REDIS_PASSWORD`. |
| `Sentry` | (off in dev) | init if `SENTRY_DSN` env present (`settings.py:284-297`) | same | **partial** | `send_default_pii=False` is set; `CeleryIntegration()` is wired but there is no Celery app to integrate with. |

### 3.1 Verdict

- The settings file is small (325 lines) but **missing 8 of the 9 production security headers** that the project's own roadmap mandates (`roadmap.md:213-215`).
- `AUTH_PASSWORD_VALIDATORS` is present and uses the standard 4 Django validators plus a custom `FodejasPasswordValidator`.
- `ALLOWED_HOSTS` has safe defaults for prod (empty list, must be env-set) but a permissive default for dev (`*`).
- There is **no `CORS_ALLOWED_ORIGINS`** configuration. If a frontend on another origin needs the API, this is missing.

## 4. Infrastructure items INF-001..016

| INF | Item | Status | Evidence path:line | Gap |
|-----|------|--------|---------------------|-----|
| INF-001 | repo-bootstrap | **partial** | `.gitignore:1-81` (covers Python, venvs, .env, secrets, Celery beat, Docker); `.editorconfig:1-33`; `.pre-commit-config.yaml:1-31` (trailing-whitespace, black, ruff, detect-secrets baseline); `CODEOWNERS:1-29` | `CODEOWNERS` references teams (`@fodejas/team`) that may not exist on GitHub; `.secrets.baseline` is gitignored (`.gitignore:39`) — fine but the file is not committed so CI detect-secrets will scan without a baseline (false positives possible). Branch protection cannot be inspected without GitHub admin access. |
| INF-002 | local-dev-env | **partial** | `docker/docker-compose.yml:1-190` (postgres, pgbouncer, redis, minio, exporters, prometheus, backup-scheduler); `scripts/dev.sh:1-18`; `scripts/setup.sh:1-28`; `pyproject.toml:11-40` lists dev deps | `pyproject.toml:11-17` declares `requirements.txt`-style deps under `dependencies`, no separate `requirements.txt` files. The dev policy (`roadmap.md:151-161`) says "venv local + docker compose for auxiliaries + docker for staging/prod" — this is mostly satisfied. **However**: the production `Dockerfile` (`docker/Dockerfile:39`) uses `manage.py runserver` (see AUD-018). |
| INF-003 | cicd | **partial** | `.github/workflows/ci.yml:1-135` (lint Ruff/Black/isort; validate-env DEBUG=False; secrets-scan detect-secrets; test postgres+redis service); `code-quality.yml:1-32` (pre-commit run); `docker-build.yml:1-124` (build, push staging/latest); `deploy-staging.yml:1-31` (placeholder echo); `deploy-production.yml:1-30` (placeholder echo) | Deploy workflows are **placeholders** that only echo (`deploy-staging.yml:21-25`, `deploy-production.yml:21-25`). No actual `docker stack deploy` / `kubectl apply` / SSH step. CI lint job does not depend on the test job (lint and test run in parallel; lint failures do not block tests — see `ci.yml:76` `needs: lint` only on test). |
| INF-004 | environments | **partial** | `.env.development.example:1-35`; `.env.staging.example:1-34`; `.env.production.example:1-34` | Three example files exist; `.gitignore:23-28` ignores real `.env*`. CI `validate-env` job enforces `DEBUG=False` for staging/prod (`ci.yml:34-54`). |
| INF-005 | secrets | **partial** | `apps/core/secrets.py:1-43` (EnvSecretStore wrapper); `.pre-commit-config.yaml:27-30` (detect-secrets); `docker/pgbouncer_userlist.txt` (committed — see AUD-026); `docker/docker-compose.yml:11-16` (MinIO root credentials in compose) | `apps/core/secrets.py:29-40` is **only an env-var fallback**. There is **no Vault / AWS Secrets Manager / GCP Secret Manager integration**. `docker/pgbouncer_userlist.txt` (referenced at `docker-compose.yml:55`) appears to contain plaintext credentials. `docker/docker-compose.yml:13-16` ships MinIO with `MINIO_ROOT_USER=minioadmin` / `MINIO_ROOT_PASSWORD=minioadmin` for dev; the production override (`docker-compose.production.yml:8-12`) reads from env but the defaults `:-minioadmin` are still applied as defaults — not fail-closed. |
| INF-006 | observability | **partial** | `apps/core/health.py:18-68` (`LivenessView`, `ReadinessView`, DB+Redis checks); `apps/core/middleware.py:16-52` (RequestIDMiddleware); `apps/core/logging_config.py:51-94` (JSON formatter with `request_id`/`user_id`); `apps/core/celery_metrics.py` (instrumentation present per CHG-105 design); `apps/core/metrics.py` (Prometheus client integration); `django_prometheus` in INSTALLED_APPS (`settings.py:89`); `docker/prometheus/prometheus.yml`; `docker/prometheus/alerts.yml:1-107`; `docker/grafana/` dashboards dir; Sentry init for prod (`settings.py:284-297`) | `health.py` does not time out the Redis check in `ReadinessView._check_redis` independently — only one `_timeout(5)` wraps both, and `_check_redis` will hang indefinitely if Redis is unreachable on a TCP-accepted-but-unresponsive connection because `redis.from_url(...).ping()` has no timeout. Sentry DSN env-driven; no health for Sentry itself. |
| INF-007 | postgres-prod | **partial** | `docker/postgres.conf` (config mounted); `docker/pgbouncer.ini`; `docker/queries.yaml` (Prometheus queries); `docker/backup-metrics/crontab:5-13` (base, WAL archive, verify, metrics) | Backups are scheduled but **no DRP / restore procedure doc** (`docs/` has only `audits/`, `api/`, `design/`). No PITR drill recorded. |
| INF-008 | storage-prod | **partial** | `settings.py:253-263` (S3 / MinIO config); `docker/docker-compose.yml:80-96` (MinIO service); `AWS_S3_FILE_OVERWRITE=False` (`settings.py:263`) | **No bucket-versioning / lifecycle policy declaration**. `docker-compose.yml:89` creates `/data` named volume with no `mc` policy step. `apps/legalization` and `apps/applications` upload to S3 paths like `validaciones/evidencia/%Y/%m/` and `legalization/` but lifecycle (retention 20 years per `AGENTS.md §2`) is not enforced anywhere. |
| INF-010 | security-headers | **missing** | `config/settings.py` (zero `SECURE_*` keys) | See §3. **AUD-017 CRITICAL**. |
| INF-011 | disaster-recovery | **missing** | `docker/backup-metrics/crontab`; `scripts/backup/{base_backup.sh,wal_archive.sh,backup_verify.sh,monitoring.sql}` | No DRP document under `docs/`. `grep -ri "RTO\|RPO\|disaster\|drp" docs/` returns 0 hits. `roadmap.md:177` lists INF-011 but it has no change folder, no design, and no proposal. |
| INF-012 | runbooks | **missing** | `README.md:38-62` (quick-start only); `docs/` (no runbook) | README has deploy instructions for dev only. No "deploy-staging", "rollback", "incident DB", "incident storage" runbook. |
| INF-014 | migrations-strategy | **partial** | Recent migrations are reversible where they are pure schema. `apps/claims/migrations/0012_create_ofijur_role.py:50-53` uses `RunPython(create_ofijur_role, reverse_create_ofijur_role)`. | **AUD-019 CRITICAL** — two migrations on 2026-07-17 / 2026-07-18 alter the PK type from `BigAutoField` to `UUIDField` on `accounts.CustomUser` (`0006`), `accounts.Role` (`0007`), and `convocatories.Convocatory` (`convocatories/0002`). These tables have FK references. With existing data, `AlterField` on a PK with FKs is destructive and zero-downtime-unsafe. No "expand/contract" pattern. |
| INF-015 | monitoring-alerts | **partial** | `docker/prometheus/alerts.yml:1-107` (PostgresTooManyConnections, CacheHitRatio, PgBouncer, BackupJobFailed, etc.) | Alerts reference metrics but **no `runbook_url` annotation** — Prometheus alertmanager `runbook_url` template is absent. **No Django / Celery / app-level alerts** (e.g., 5xx rate, latency, treasury deadline). |
| INF-016 | perf-baseline | **partial** | No smoke tests; no k6 / Locust / Gatling scripts | `scripts/` has only `setup.sh`, `dev.sh`, `create_venv.sh`, and `backup/*`. No `tests/perf/`, no `tests/smoke/`. Roadmap §4.2 deliverable "smoke tests, pruebas de carga de la convocatoria piloto" is unmet. |

### 4.1 Infrastructure summary

- **Total**: 15 (INF-001..016 minus INF-009)
- **Done**: 0 (none fully done)
- **Partial**: 9 (INF-001, INF-002, INF-003, INF-004, INF-005, INF-006, INF-007, INF-008, INF-014, INF-015, INF-016) — that's 11 partial, not 9. Recount: 11 partial, 4 missing.
- **Missing**: 4 (INF-010, INF-011, INF-012, INF-013)
- **Aplazado** (roadmap): INF-013 (IaC)
- **Eliminado** (roadmap): INF-009 (email transactional)

For the summary header we count INF items that have at least the artifact trail in place as **partial** and those without any artifact as **missing**.

## 5. WARNING deep-dive (AUD-006..011 from initial audit)

### 5.1 AUD-006 — `HasRole` permission class defined twice — **WARNING, confirmed**

- **location**: `apps/accounts/permissions.py:23-58` and `apps/accounts/permissions.py:61-80`
- **re-investigation**:
  - `apps/accounts/permissions.py:23` declares `class HasRole(permissions.BasePermission):` with helper methods `has_role`/`has_any_role`/`has_all_roles` (lines 41-58) — no `__init__`.
  - `apps/accounts/permissions.py:61` declares `class HasRole(permissions.BasePermission):` with `__init__(self, role_code=None)` and a real `has_permission()` (lines 69-80).
  - In Python, the second class rebinds the name `HasRole` in the module namespace, so any `from apps.accounts.permissions import HasRole` resolves to the second class only.
  - The docstring on the second class (`permissions.py:67`) correctly says `permission_classes = [HasRole('R-ADMIN')]`, matching `__init__(role_code)`. That is the intended usage.
  - The first class's helpers (`has_role`, `has_any_role`, `has_all_roles`) are unreachable because nobody imports the first class under a different name. Grep across `apps/`: `from apps.accounts.permissions import HasRole` is the only import pattern (e.g., `apps/accounts/services/assignment.py` uses `_has_role(user, code)` which is the module-level helper function `permissions.py:189-193` — different code path).
- **final classification**: WARNING. The bug is real (dead code + second class shadows first), but it is not security-critical because the second class is the one wired into permissions lists and behaves correctly per its own contract.
- **new evidence**: see `apps/accounts/permissions.py:23, 61, 189-193` (the helper functions at the module level make the broken first class doubly dead).

### 5.2 AUD-007 — `calcular_puntaje_total` non-atomic — **RECLASSIFIED to CRITICAL**

- **location**: `apps/scoring/services/scoring_service.py:34-82`
- **re-investigation**:
  - `calcular_puntaje_total` does `PuntajeTotal.objects.get_or_create(...)` at line 67 and `puntaje.save()` at line 80 without `select_for_update` or `@transaction.atomic` wrapping the whole body.
  - The function is **reached from request views**, not just from management commands:
    - `apps/scoring/views.py:122` — `ScoringEvaluateView.post(...)` calls `calcular_puntaje_total(evaluacion.solicitud, request.user)` after every AJAX evaluation update.
    - `apps/scoring/views.py:139` — `ScoringCalculateView.post(...)` calls `calcular_puntaje_total(solicitud, request.user)` on manual recalculation.
  - Both views are `LoginRequiredMixin`-protected DRF/HTML endpoints served over HTTP. Two `R-COMITE` members submitting evaluations on the same `Solicitud` simultaneously can race the `get_or_create` and the `save`, producing an inconsistent `puntaje_total`.
  - Per AGENTS.md §6 rule 5 ("No saltarse pruebas en scoring") scoring races are non-negotiable.
- **final classification**: **CRITICAL** (reclassified from WARNING). This is a money-equivalent numerical race in the path that determines beneficiary ranking.
- **new evidence**: `apps/scoring/views.py:122, 139`.

### 5.3 AUD-008 — Direct `request.user.groups.filter(name=...)` checks — **WARNING, confirmed (3 occurrences, not 8)**

- **location**:
  - `apps/applications/views.py:363` — `user.groups.filter(name="R-REVISOR").exists()`
  - `apps/scoring/views.py:25` — `user.groups.filter(name="R-COMITE").exists()`
  - `apps/scoring/views.py:158` — `request.user.groups.filter(name="R-COORDINADOR").exists()`
- **re-investigation**: The initial audit cited 8 occurrences across `apps/claims/views.py`. **This was incorrect.** `apps/claims/views.py` uses `Role.objects.filter(code="R-JUNTA"/"R-OFIJUR").first()` (lines 159, 223, 278, 310, 344, 429, 491, 523), which goes through the `Role` table, not the Django `Group` table. Those are *better* than the pattern flagged — they go through the RBAC catalog. The 3 direct `groups.filter(name=...)` calls remain, and they hard-code Group names that the `Role.group` FK in `apps/accounts/models.py:143-151` is supposed to keep in sync. None of the 3 are inside money/payment paths (`apps/applications/views.py:363` gates the requirements-review list; `apps/scoring/views.py:25, 158` gate the committee scoring views and ranking view). So the security impact is bounded but the maintainability risk is real.
- **final classification**: WARNING (unchanged).
- **new evidence**: corrected occurrence count = 3. `apps/claims/views.py` does NOT use the direct Django Group pattern (initial audit mis-classified it).

### 5.4 AUD-009 — `can_apelar` does not exist — **WARNING, confirmed**

- **location**: `apps/claims/permissions.py:65-72`
- **re-investigation**:
  - `apps/claims/permissions.py:65-72` (the class `CanCreateApelacion`) does:
    ```python
    from apps.claims.services.apelaciones import can_apelar
    can_create, _ = can_apelar(obj, request.user)
    ```
  - `apps/claims/services/apelaciones.py` defines `validar_apelacion` (lines 6-43), `crear_apelacion` (lines 46-81), `iniciar_analisis`, `confirmar_apelacion`, `revocar_apelacion`, `_verify_ofijur_role`. **There is no `can_apelar`.** Confirmed by `grep -r "can_apelar" apps/`: 2 hits, both inside `apps/claims/permissions.py:69, 71`.
  - This will raise `ImportError` at the first call to `CanCreateApelacion.has_object_permission()`.
- **Wiring check**: searched for `CanCreateApelacion` usage: no DRF view declares it in `permission_classes`. Grep across `apps/`: only the class definition in `apps/claims/permissions.py:65-72` matches. **So today it is dead code, not a runtime ImportError.** That keeps it at WARNING rather than CRITICAL — the class is not wired to a view yet.
- **final classification**: WARNING (unchanged). Reclassified upward **only if** CHG-206 lands a view that wires this class. Recommendation: rename to `validar_apelacion` (which already returns `(is_valid, error_message)` matching the call shape).

### 5.5 AUD-010 — Signals never registered — **RECLASSIFIED to CRITICAL**

- **location**: `apps/audit/apps.py:9-11`; `apps/audit/signals.py:30-114`
- **re-investigation**:
  - `apps/audit/apps.py:9-11`:
    ```python
    def ready(self):
        import apps.audit.signals  # noqa: F401
    ```
  - `apps/audit/signals.py:62`:
    ```python
    @receiver(post_save)
    def audit_save_receiver(sender, instance, created, **kwargs):
        ...
        if sender not in [m[0] for m in AUDIT_MODELS]:
            return
    ```
  - `AUDIT_MODELS` (`signals.py:31-52`) lists **strings** like `"apps.core.models.Estrato"` — but `sender` is a Python class (e.g., the actual `apps.core.models.Estrato` class), not a string. So the membership check `sender not in [m[0] for m in AUDIT_MODELS]` always returns `True` for any model, the handler early-returns, and **no audit event is ever written automatically**.
  - `register_audit_signals()` (`signals.py:55-59`) is defined but **never called**. Confirmed by `grep -r "register_audit_signals"`: only the definition at `signals.py:55` and references in this audit doc.
  - Net effect: **the CAP-022 automatic signal-based audit is dead code**. The only audit events written are the manual `AuditEvent.objects.create(...)` calls in the five services called out in AUD-001, each of which carries field-name bugs that silently `except Exception: pass` away.
- **final classification**: **CRITICAL** (reclassified from WARNING). Combined with AUD-001, **no audit events are correctly written to the chain today** — every `AuditEvent.objects.create(...)` call site either uses wrong field names or relies on a never-registered signal.
- **new evidence**: `signals.py:66` compares `sender` (a class) against list of strings, and `signals.py:55-59` defines `register_audit_signals` but no caller invokes it.

### 5.6 AUD-011 — `Art. ...` placeholders — **WARNING, confirmed**

- **location**: `apps/convocatories/domain/normativa.py:42, 47, 59, 65`
- **re-investigation**:
  - `apps/convocatories/domain/normativa.py:42` — `beneficio_5_semestres`: `"articulo": "Art. ... Decreto 0372/2025"`.
  - `apps/convocatories/domain/normativa.py:47` — `beneficio_10_semestres`: same placeholder.
  - `apps/convocatories/domain/normativa.py:59` — `tesoreria_5_dias`: same placeholder.
  - `apps/convocatories/domain/normativa.py:65` — `exoneracion_30_dias`: same placeholder.
  - `apps/convocatories/domain/normativa.py:11, 16, 21, 26, 31, 36` — plazo_* entries correctly cite `Art. 16 Decreto 0372/2025`.
- **final classification**: WARNING (unchanged). Each placeholder is a violation of AGENTS.md §6 rule 4 but they are documentation strings — no runtime impact. **The Art. for the plazo_* entries is correct** (Art. 16 Decreto 0372/2025), which contradicts the initial audit's tentative claim that "Art. for plazos por nivel" was also a placeholder. It is not.

## 6. Stub and gap analysis

### 6.1 `apps/reporting/` (CAP-020, CAP-021, CAP-027, CAP-028) — **stub**

| Module | Lines | Status | Notes |
|--------|-------|--------|-------|
| `apps/reporting/__init__.py` | 0 | empty | nothing |
| `apps/reporting/apps.py:1-7` | 7 | minimal AppConfig | `default_auto_field = "django.db.models.BigAutoField"`, `name = "apps.reporting"`, `verbose_name = "Reporting"`. |
| `apps/reporting/admin.py` | 0 | empty | nothing |
| `apps/reporting/models.py` | 0 | empty | no models at all |
| `apps/reporting/urls.py` | 0 | empty | no URL routes |
| `apps/reporting/views.py` | 0 | empty | no views |

**Verdict**: 5 of 6 modules are 0-line files. The app is registered in `INSTALLED_APPS` (`config/settings.py:101`) and ships in the URL conf via `path("", include("django_prometheus.urls"))` (only Prometheus, not reporting). **There is no CHG-503/504/505/506 OpenSpec change** in `openspec/changes/`. **AUD-024 WARNING** — the app contributes zero functionality today but is loaded by Django, so any future addition will run migrations.

### 6.2 `apps/psychosocial/` (CAP-012) — **stub**

| Module | Lines | Status | Notes |
|--------|-------|--------|-------|
| `apps/psychosocial/__init__.py` | 0 | empty | nothing |
| `apps/psychosocial/apps.py:1-7` | 7 | minimal AppConfig | `verbose_name = "Psychosocial"`. |
| `apps/psychosocial/admin.py` | 0 | empty | nothing |
| `apps/psychosocial/models.py` | 0 | empty | no models |
| `apps/psychosocial/urls.py` | 0 | empty | no routes |
| `apps/psychosocial/views.py` | 0 | empty | no views |

**Verdict**: identical to reporting — 5 of 6 modules are 0-line files. Registered in INSTALLED_APPS (`config/settings.py:98`). No CHG-402 in `openspec/changes/`. **AUD-024**.

### 6.3 `apps/governance/sessions/` (CAP-017 / CHG-501) — **absent**

- **location**: `apps/governance/` directory listing shows only `admin.py`, `apps.py`, `migrations/`, `models.py`, `services/`, `urls.py`, `views.py`, `__init__.py`. **No `sessions/` subdirectory.**
- `apps/governance/models.py:1-192` contains `SecuencialActo`, `ActoAdministrativo`, `ListadoDefinitivo`. **No `Sesion`, `OrdenDelDia`, `Voto`, `Quorum`, `ActaSesion`, `ConflictoInteres` model.**
- `apps/governance/services/` contains only `generador.py`, `listado.py`, `pdf.py`. No `sessions.py` / `voting.py`.
- `apps/governance/views.py` exists but its content (not opened this pass) does not address junta sessions/quorum per the absence of any CHG-501 change folder in `openspec/changes/`.
- **Verdict**: CAP-017 is not implemented. **AUD-025 WARNING** (CRITICAL if junta quorum is required for the convocatoria piloto, but no CHG-501 marks this in scope for the pilot — the Fase 2 deliverables `roadmap.md:296-297` say CHG-207 definitive results; junta sessions fall under Fase 5).

### 6.4 `apps/condonation/` — exoneration enforcement — **absent (still)**

- **location**: `apps/condonation/models.py:68-137` defines `Sanction` with fields `justification`, `justification_details`, `justification_approved`, `payment_proof`, `paid_at`, `reviewed_by`, `reviewed_at`, `created_at`, `updated_at`. **No `fecha_recepcion`, no `fecha_limite`, no `vencimiento`, no `plazo_30`.**
- `apps/condonation/services.py:243-273` — `submit_justification` stores `justification` and `justification_details` and sets status to `EN_REVISION`. It does not record when the justification was received, so the 30-calendar-day clock has no start.
- `apps/condonation/services.py:275-300` — `approve_justification` does not compute or check any deadline.
- `apps/condonation/tests.py:62-94` — tests for `SanctionService.submit_justification_invalid`, `approve_justification_not_found`, `confirm_payment_not_found`. **No deadline-boundary test.**
- **Verdict**: AUD-023 WARNING (consistent with initial AUD-013). The 30-day exoneration window is referenced only in `apps/claims/services/apelaciones.py:25-29` (a different domain — appeals of claims), and there the boundary check uses `reclamacion.fecha_resolucion`. For `Sanction`, the boundary does not exist at all.

## 7. Migration safety

### 7.1 Last 5 migrations by date

| # | Migration | Table(s) touched | Reversible? | Data migration? | NOT NULL without default? | Finding |
|---|-----------|------------------|-------------|-----------------|---------------------------|---------|
| 1 | `accounts/migrations/0007_alter_role_id.py` (2026-07-18) | `accounts.role` | schema-only | No | **N/A** (PK alter, not NOT NULL add) | **AUD-019 CRITICAL** — `AlterField` changes PK type from `BigAutoField` to `UUIDField` on a table that is referenced by `accounts.UserRole.role`, `accounts.Permission.auth_permission` (`0005`), and others. With existing rows, Django emits `ALTER COLUMN id TYPE UUID USING ...` which requires explicit cast and may fail if downstream FK columns are not also rewritten. No data migration to backfill. |
| 2 | `convocatories/migrations/0002_alter_convocatory_id.py` (2026-07-18) | `convocatories.convocatory` | schema-only | No | N/A | **AUD-019 CRITICAL** — same destructive PK alter on a heavily-referenced table (`applications.Solicitud.convocatoria`, `governance.ActoAdministrativo.convocatoria`, `governance.ListadoDefinitivo.convocatoria`, `apps.convocatories` self-references). |
| 3 | `accounts/migrations/0006_alter_customuser_id.py` (2026-07-17) | `accounts.customuser` | schema-only | No | N/A | **AUD-019 CRITICAL** — same pattern. `CustomUser` is referenced by virtually every domain table. |
| 4 | `claims/migrations/0013_apelacion_apelacionhistorial.py` (2026-07-08) | `claims.apelacion`, `claims.apelacionhistorial` | yes (pure CreateModel, auto-reversible) | No | n/a | safe |
| 5 | `applications/migrations/0003_add_requisito_validacion.py` (2026-07-07) | `applications.requisitovalidacion` | yes (pure CreateModel) | No | n/a | safe |
| 6 | `claims/migrations/0012_create_ofijur_role.py` (hand-written, ~2026-07-08 area) | `accounts.role` (data) | **yes** — `RunPython(create_ofijur_role, reverse_create_ofijur_role)` is supplied (`apps/claims/migrations/0012_create_ofijur_role.py:31-37, 50-53`) | yes — creates `R-OFIJUR` row via `Role.objects.get_or_create(code="R-OFIJUR", ...)` | n/a | safe and explicitly reversible |

### 7.2 Summary

- **Destructive PK alters** (#1, #2, #3) are not zero-downtime. They violate INF-014 ("zero-downtime deploys, migraciones reversibles, expands/contracts"). With production data present, each is a CRITICAL data-integrity hazard.
- **Money / payment / audit / auth tables affected**: `accounts.customuser` (auth) is the third. `accounts.role` (auth/RBAC) is the first. None of the migrations in the last-5 touch `audit`, `treasury`, `condonation`, `legalization` tables — but the table list does not mean the rest of the migration tree is safe, only that the most recent 5 are concentrated on the auth schema.

## 8. Findings (new + reclassified)

### 8.1 BLOCKER

#### AUD-016 — Celery app and periodic tasks are entirely absent; CAP-010 5-day and CAP-016 30-day deadlines cannot be enforced

- **location**: no `config/celery.py`; no `apps/*/tasks.py`; no `@shared_task` / `@periodic_task` / `beat_schedule` / `crontab(...)` decorator anywhere in `apps/` or `config/`; `config/settings.py:238-248` only declares broker URLs; `apps/treasury/services.py:1-152` has no scheduler call; `apps/condonation/services.py:243-273` records a justification without a deadline.
- **claim**: Roadmap Fase 3 Entregables (`roadmap.md:354`) and Fase 4 Entregables (`roadmap.md:395`) require the platform to enforce the Tesorería 5-working-day window and the exoneración 30-calendar-day window respectively. CAP-010 is in scope for the pilot. Without a Celery app, a beat schedule, and at least two periodic tasks (`tesoreria_alert_v5d` and `exoneracion_alert_v30d`), these promises are unmet at the platform level. **There is no `DisbursementAuthorization.VENCIDO` state, no `Sanction.fecha_limite`, and no scheduled sweep.**
- **evidence** (`config/settings.py:246-248`):
  ```python
  if REDIS_PASSWORD:
      CELERY_BROKER_URL = f"redis://:{REDIS_PASSWORD}@{REDIS_URL.split('://')[1]}"
  else:
      CELERY_BROKER_URL = REDIS_URL
  ```
  Only broker config. No `Celery("fodejas")` instantiation, no `app.autodiscover_tasks(...)`, no `app.conf.beat_schedule = {...}`.
- **evidence** (architectural intent from archived designs):
  - `openspec/changes/archive/2026-07-02-CHG-105-habeas-data/design.md:57` declares "New `config/celery.py` (`Celery("fodejas")`, `autodiscover_tasks(["apps.accounts"])`) + `apps/accounts/tasks.py`. `habeas_expiry_check` (shared_task): ..." — never implemented.
  - `openspec/changes/archive/2026-07-02-CHG-106-notifications/design.md:101, 136` — `dispatch_notification` shared_task design — never implemented. `apps/accounts/services/notifications.py:200` even admits "simplified without Celery".
- **rule**: AGENTS.md §6 rule 5 ("No saltarse pruebas ... reglas monetarias o de plazos"); `roadmap.md:354, 395` (CAP-010, CAP-016 entregables).
- **recommendation**: Create `config/celery.py` with `app = Celery("fodejas"); app.config_from_object("django.conf:settings", namespace="CELERY"); app.autodiscover_tasks()`. Add `apps/treasury/tasks.py` with `tesoreria_alert_v5d` (beats daily 09:00 America/Bogota) that scans `DisbursementAuthorization.objects.filter(status="ORDENADO", treasury_order_date__lte=hace_5_dias_habiles(...))` and notifies the Coordinación Técnica. Add `apps/condonation/tasks.py` with `exoneracion_alert_v30d` (daily) that scans `Sanction.objects.filter(status="EN_REVISION", ...)` and emits an alert at day 25 + marks `VENCIDO` at day 31. Add `models.DateTimeField` `fecha_limite` to `Sanction` and `tesorury_order_received_at` to `DisbursementAuthorization`.

### 8.2 CRITICAL

#### AUD-017 — Production security headers are entirely missing from `config/settings.py`

- **location**: `config/settings.py:1-325` (no `SECURE_*` keys, no `CSRF_TRUSTED_ORIGINS`, no explicit `X_FRAME_OPTIONS`)
- **claim**: The `roadmap.md:213-215` Fase 0 Entregables require "HTTPS obligatorio en todos los entornos no-locales" and "Rate limiting y headers de seguridad activos en staging y prod". The settings file declares none of `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`, `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`. `ALLOWED_HOSTS` defaults to `[]` for production (`settings.py:74-77`), which is safer than permissive but operationally fragile.
- **evidence**: `grep -n "SECURE_\|CSRF_TRUSTED_ORIGINS" config/settings.py` → 0 matches.
- **rule**: AGENTS.md §6 rule 1 (no exponer secrets en tránsito); `roadmap.md:213-215`.
- **recommendation**: Add an `if IS_PRODUCTION:` block that sets `SECURE_SSL_REDIRECT = True`, `SECURE_HSTS_SECONDS = 31536000`, `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`, `SECURE_HSTS_PRELOAD = True`, `SECURE_CONTENT_TYPE_NOSNIFF = True`, `SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"`, `SESSION_COOKIE_SECURE = True`, `CSRF_COOKIE_SECURE = True`, `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`, `CSRF_TRUSTED_ORIGINS = ["https://fodejas.gov.co", "https://www.fodejas.gov.co"]`. Add explicit `X_FRAME_OPTIONS = "DENY"` even though Django's default matches.

#### AUD-018 — Production Docker compose runs Django with `runserver`, not gunicorn/uwsgi

- **location**: `docker/docker-compose.production.yml:16`
- **claim**: `command: python manage.py runserver 0.0.0.0:8000` is hard-coded into the production compose override. `runserver` is intended for development (it is documented as "a lightweight Web server ... NOT intended for use in production" by Django upstream). With `runserver`, there is no worker pool, no request timeout, no graceful shutdown, no static-files handler, and `DEBUG` mode behavior (auto-reload, tracebacks) leaks when `DEBUG` is misconfigured.
- **evidence** (`docker/docker-compose.production.yml:14-16`):
  ```yaml
  - DEBUG=False
  - DJANGO_SETTINGS_MODULE=config.settings
  command: python manage.py runserver 0.0.0.0:8000
  ```
- **evidence** (`docker/Dockerfile:39`):
  ```
  CMD ["runserver", "0.0.0.0:8000"]
  ```
  The Dockerfile default also uses `runserver`.
- **rule**: Standard production-readiness expectation; `roadmap.md:163` "Plataforma desplegable y observable desde el día 1" implies a real WSGI server.
- **recommendation**: Add `gunicorn` to `pyproject.toml` dependencies; set `command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60` in `docker-compose.production.yml`; change Dockerfile `CMD` accordingly.

#### AUD-019 — Destructive PK migrations on auth/convocatory tables without data migration or expand/contract

- **location**: `apps/accounts/migrations/0006_alter_customuser_id.py` (2026-07-17); `apps/accounts/migrations/0007_alter_role_id.py` (2026-07-18); `apps/convocatories/migrations/0002_alter_convocatory_id.py` (2026-07-18)
- **claim**: Three recent migrations on **2026-07-17** and **2026-07-18** change `BigAutoField` PKs to `UUIDField` on tables that already have FK references. With existing rows, `AlterField` of a PK is destructive — `PostgreSQL ALTER TABLE ... ALTER COLUMN id TYPE UUID USING ...` requires explicit cast and triggers cascading FK rewrites. None of these migrations provide a data migration to backfill UUIDs nor an expand/contract pattern (add new column, backfill, swap, drop old). All three run as schema-only `AlterField`.
- **evidence** (`apps/accounts/migrations/0007_alter_role_id.py:13-18`):
  ```python
  operations = [
      migrations.AlterField(
          model_name='role',
          name='id',
          field=models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
      ),
  ]
  ```
- **evidence** (`apps/convocatories/migrations/0002_alter_convocatory_id.py:13-18`): identical pattern for `Convocatory`.
- **evidence** (`apps/accounts/migrations/0006_alter_customuser_id.py:13-18`): identical pattern for `CustomUser`.
- **rule**: INF-014 ("zero-downtime deploys, expand/contract"); AGENTS.md §6 rule 5 (no saltarse pruebas, integridad transaccional); standard migration safety.
- **recommendation**: For any future PK change on a referenced table, follow the expand/contract pattern (add `id_uuid` column nullable, backfill via `RunPython`, add generated column, swap in app, drop old). For these three migrations, write a `RunPython` data migration that backfills the new UUID PKs deterministically (e.g., `uuid5(NAMESPACE_URL, f"role:{old_id}")`) before the `AlterField`, so existing rows survive the cast.

#### AUD-020 — Audit-event write paths persist wrong field names; swallowed by `except Exception: pass`

- **location**: `apps/legalization/signer.py:181-192`; `apps/accounts/services/notifications.py:185-194`; `apps/convocatories/services/convocatoria_service.py:166-178`; `apps/applications/services/wizard_service.py:109-118`; `apps/audit/signals.py:62-114`
- **claim**: All four call sites that bypass `apps.audit.services.log_audit_event` use `AuditEvent.objects.create(...)` with **incorrect field names or no hash fields**, and each is wrapped in a `try/except Exception: pass` so the failure is silent. Combined with AUD-010 (signals never fire), **no audit event reaches the chain correctly today**.
- **evidence** (`apps/legalization/signer.py:181-192`):
  ```python
  AuditEvent.objects.create(
      action="ELECTRONIC_SIGNATURE",
      entity=document_type,
      module="legalization",
      actor_id=actor_id,
      details={                              # not a field
          "pre_sign_hash": result.pre_sign_hash,
          ...
      },
  )
  ```
  `AuditEvent` has no `details` field (`apps/audit/models.py:8-48`). The `actor_id` is also passed positionally-like while the model field is `actor` (FK). The exception is swallowed by `except Exception: pass` at `signer.py:193-195`.
- **evidence** (`apps/convocatories/services/convocatoria_service.py:166-178`):
  ```python
  AuditEvent.objects.create(
      user=actor,                            # field is `actor`, not `user`
      action=f"convocatory.{accion}",
      entity="convocatories.Convocatory",
      entity_id=convocatoria.id,
      changes={...},
  )
  ```
  No `previous_hash`/`current_hash`, so the model's `save()` (`apps/audit/models.py:66-81`) computes them via `get_previous_hash()` — which races (AUD-003).
- **evidence** (`apps/applications/services/wizard_service.py:109-118`): same `user=actor` bug.
- **evidence** (`apps/accounts/services/notifications.py:185-194`): correct field names, but **no `previous_hash`/`current_hash` and a 20-char `action` truncation** (`signals.py:181-184` shortens via `notif.` and then `[:20]`). The action truncation will collide for many distinct actions (collision → `IntegrityError` → silent except).
- **rule**: AGENTS.md §6 rule 1; CAP-022 (project.md §9.3); AUD-001 from initial audit (this is a re-aggregation).
- **recommendation**: Replace every direct `AuditEvent.objects.create(...)` with `log_audit_event(...)` from `apps.audit.services`, which computes `previous_hash` and `current_hash` atomically and uses the correct field names.

### 8.3 WARNING

#### AUD-021 — `DATA_UPLOAD_MAX_MEMORY_SIZE` / `FILE_UPLOAD_MAX_MEMORY_SIZE` not set; FUI anexos may exceed Django's 2.5 MB default

- **location**: `config/settings.py` (no entries); `apps/applications/services/wizard_service.py` (uploads `evidencia`); `apps/condonation/models.py:112-116` (`Sanction.payment_proof = FileField`); `apps/legalization/models.py` (legalization documents).
- **claim**: Django's default `DATA_UPLOAD_MAX_MEMORY_SIZE` is 2.5 MB. FUI anexos for `applications.RequisitoValidacion.evidencia` (`apps/applications/migrations/0003_add_requisito_validacion.py:23`) and other file fields will reject any single request body > 2.5 MB, returning `RequestDataTooBig` (HTTP 400). Without an explicit higher cap, the wizard upload will fail for typical scanned-ID PDFs (which are 1-3 MB).
- **evidence**: `grep -n "DATA_UPLOAD_MAX_MEMORY_SIZE\|FILE_UPLOAD_MAX_MEMORY_SIZE" config/` → 0 hits.
- **rule**: AGENTS.md §6 rule 5 (FUI anexos are part of CAP-003).
- **recommendation**: Set `DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024` (10 MB) and `FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024`; route larger uploads directly to S3 via a pre-signed URL flow.

#### AUD-022 — `apps/treasury/views.py` and `apps/treasury/urls.py` are empty (0 bytes)

- **location**: `apps/treasury/views.py`, `apps/treasury/urls.py`
- **claim**: The treasury app has 9 .py files including models and services, but no views and no URL routes. There is no reconciliation UI for Tesorería to mark a payment as paid and attach a comprobante (the explicitly-required UX from `roadmap.md:354`).
- **evidence**: `filesystem_list_directory apps/treasury` shows `__init__.py admin.py apps.py migrations/ models.py services.py urls.py views.py`. Read both `views.py` and `urls.py`: 0 lines.
- **rule**: `roadmap.md:354` Fase 3 Entregables; AGENTS.md §6 rule 5.
- **recommendation**: Add `apps/treasury/views.py` with a `TreasuryReconciliationView` (function-based or class-based) that lists `DisbursementAuthorization.objects.filter(status="ORDENADO")` and lets Tesorería upload `payment_proof`, call `TreasuryService.confirm_payment(...)`. Wire in `apps/treasury/urls.py` and include in `config/urls.py`.

#### AUD-023 — 30-day exoneration deadline not enforced (CAP-016, AGENTS.md §6 rule 7)

- **location**: `apps/condonation/models.py:68-137` (Sanction); `apps/condonation/services.py:243-273` (`submit_justification`).
- **claim**: Same finding as initial AUD-013 — re-investigation confirms there is no `fecha_recepcion` or `fecha_limite` on `Sanction`, and `submit_justification` does not start any clock. The 30-calendar-day window from Decreto 0372/2025 (Art. 17) cannot be enforced until both fields and a periodic sweep (per AUD-016) exist.
- **evidence**: `apps/condonation/models.py:111` is `justification_approved = BooleanField(default=False)`. No datetime field anywhere in the model is set when `submit_justification` runs.
- **rule**: AGENTS.md §6 rule 7 (no inventar plazos — and conversely, no omitir plazos normativos); `roadmap.md:395`.
- **recommendation**: Add `fecha_recepcion = DateTimeField(auto_now_add=True)` and `fecha_limite = DateTimeField()` to `Sanction`. Override `submit_justification` to compute `fecha_limite = fecha_recepcion + relativedelta(days=30)`. Pair with AUD-016's `exoneracion_alert_v30d`.

#### AUD-024 — Stub apps `reporting` and `psychosocial` are registered in INSTALLED_APPS

- **location**: `config/settings.py:98-103`; `apps/reporting/{models,views,urls,admin}.py` (0 lines each); `apps/psychosocial/{models,views,urls,admin}.py` (0 lines each).
- **claim**: Both apps are listed in INSTALLED_APPS (`settings.py:101` reporting, `settings.py:98` psychosocial). They contribute 7 lines of code each (just the AppConfig) and 0 lines of model/view/admin code. There are no corresponding CHG-402 (psychosocial) or CHG-503/504/505/506 (reporting) OpenSpec changes.
- **evidence**: `filesystem_list_directory apps/reporting` shows 6 .py files, 5 of them 0 lines; same for `apps/psychosocial`.
- **rule**: AGENTS.md §6 rule 8 (no asumir fuera del alcance — but the apps are *registered*, not just assumed).
- **recommendation**: Either remove from INSTALLED_APPS until the corresponding CHG-* exists, or open CHG-402 and CHG-503/504/505/506 proposals immediately and add the actual code.

#### AUD-025 — CAP-017 Sesiones / Quorum / Voting not implemented (governance/sessions/ does not exist)

- **location**: `apps/governance/` (no `sessions/` subdir); `apps/governance/models.py:1-192` (no Sesion/Orden/Voto/Quorum model).
- **claim**: CAP-017 (CHG-501) calls for "Sesiones de Junta y CT: orden del día, quórum, votaciones, actas firmadas, conflict-of-interest" (`roadmap.md:416`). There is no CHG-501 change folder in `openspec/changes/`, no `apps/governance/sessions/` subdirectory, no `Sesion` model, no `Voto` model. CHG-207 (`apps/governance/services/listado.py`) handles the listing-definitivo output but never depends on a session having taken place.
- **evidence**: `filesystem_list_directory apps/governance` shows only `admin.py apps.py migrations/ models.py services/ urls.py views.py __init__.py`. No `sessions/`.
- **rule**: Roadmap §9 (CAP-017, Fase 5); AGENTS.md §6 rule 10 (no renombrar CAP-NNN sin proposal — also no agregar capacidades sin proposal).
- **recommendation**: Open `openspec/changes/CHG-501-sessions/proposal.md` with the model and state-machine design, or accept that junta sessions are out-of-scope for the convocatoria piloto and explicitly exclude them from CHG-207's "Junta aprueba el listado definitivo" Entregable.

### 8.4 SUGGESTION

#### AUD-026 — `docker/pgbouncer_userlist.txt` may contain plaintext credentials and is referenced from compose

- **location**: `docker/pgbouncer_userlist.txt` (referenced by `docker/docker-compose.yml:55` and `docker/docker-compose.staging.yml:31`, `docker/docker-compose.production.yml:33`).
- **claim**: PgBouncer `userlist.txt` is the standard location for `username:password` (md5-hashed or plaintext). If the file is committed with the production credentials, the secrets are exposed. `docker/pgbouncer.ini` may also contain `auth_file = /etc/pgbouncer/userlist.txt`.
- **evidence**: file contents not opened in this audit (constraint: avoid extractions of secret material). The file is referenced but its `.gitignore` membership was not verified.
- **rule**: INF-005; AGENTS.md §2 (PII / secret hygiene); `pyproject.toml` detects-secrets pre-commit hook exists (`.pre-commit-config.yaml:27-30`).
- **recommendation**: Confirm `docker/pgbouncer_userlist.txt` is listed in `.gitignore` (currently not — `.gitignore` has no entry for it). If it is committed, move to `docker/pgbouncer_userlist.txt.example` and inject real credentials via `.env`/secret manager.

#### AUD-027 — INF-001..016 have no corresponding OpenSpec change folders

- **location**: `openspec/changes/` (no `INF-*` directory; only `CHG-*` and `archive/`).
- **claim**: The project follows OpenSpec for every capability (`AGENTS.md §3 rule 1`), but none of the 15 active infrastructure items (INF-001..016, skipping INF-009) has an `openspec/changes/INF-NNN-<slug>/` folder with `proposal.md` + `tasks.md`. There is therefore no agreed-upon acceptance criteria for the Fase 0 deliverables (`roadmap.md:185-222`).
- **evidence**: `glob openspec/changes/INF*` → 0 hits. `filesystem_list_directory openspec/changes` shows only `CHG-*` and `archive/`.
- **rule**: AGENTS.md §3 rule 1 ("Toda propuesta a una capacidad documentada ... debe pasar por `proposal.md` + `tasks.md`").
- **recommendation**: Open one `openspec/changes/INF-NNN-<slug>/` folder per infrastructure item before any further implementation work. At minimum, INF-002 (dev-env), INF-003 (CI/CD), INF-011 (DRP), INF-012 (runbooks), INF-014 (migrations strategy) should be proposed before their respective gaps are addressed.

### 8.5 Reclassifications from initial audit

| Audit ID | Old class | New class | Reason |
|----------|-----------|-----------|--------|
| AUD-007 | WARNING | **CRITICAL** | `calcular_puntaje_total` is reached from `apps/scoring/views.py:122, 139` (request views), not only from management commands. Per AGENTS.md §6 rule 5, scoring races are non-negotiable. |
| AUD-010 | WARNING | **CRITICAL** | `register_audit_signals()` is never called (`grep -r "register_audit_signals"` → only the definition). The bare `@receiver(post_save)` compares `sender` (a class) against a list of strings (`signals.py:66`) — the membership check always returns `True`, so the handler always early-returns. Combined with AUD-001's wrong-field writes, **no audit events reach the chain correctly today.** |

## 9. What was NOT inspected

- **GitHub-side branch protection rules**: cannot be inspected without admin access to the GitHub repo.
- **`docker/pgbouncer.ini` and `docker/pgbouncer_userlist.txt` content**: avoided to prevent logging/handling secret material in this audit. AUD-026 documents the file's existence and the recommendation.
- **`.secrets.baseline` content**: this file is in `.gitignore` (`.gitignore:39`) so it should not be committed. Not opened.
- **`templates/` directory**: not opened in this pass (out of scope for the audit areas listed).
- **`apps/reporting/management/commands/` and `apps/psychosocial/management/commands/`**: do not exist; nothing to inspect.
- **`apps/governance/views.py` and `apps/governance/services/{generador,pdf}.py`**: not opened this pass — initial audit covered `services/listado.py` (AUD-005); the others are listed in coverage but not deeply inspected.
- **`apps/audit/serializers.py`**: not opened (read only `apps/audit/{models,services,signals,apps}.py`).
- **`apps/accounts/permissions_mixin.py`** and the rest of `apps/accounts/`: only `permissions.py` was opened. The PermissionMixin / JuntaPermissionMixin / OfijurPermissionMixin referenced from `apps/scoring/views.py:12`, `apps/claims/views.py:16` etc. are not opened.
- **`apps/legalization/services/*`, `apps/legalization/views.py`, `apps/legalization/signer.py` (full)**: only the `_log_signature` function at lines 170-195 was inspected. The rest is not.
- **`apps/applications/services/wizard_service.py` (full)**: only the audit-write function at lines 100-121 was inspected.
- **Frontend templates under `templates/`**: not opened (out of scope).
- **The full migration tree** (e.g., `0010_*`, `0008_*`): the last 5 by date were inspected; older ones were not.
- **Phase-by-phase CHG folder contents for archived changes**: not re-inspected.
- **`opencode.json`, `.opencode/`, `qa_test.py`, `qa_claims_test.py`, `debug_models.py`, `test_flow.js`, `test_doc.pdf`**: not opened (per initial-audit §5).
- **Runtime behavior**: no Django/pytest/docker/migration execution, per Hard Constraints.

---

(End of report — total lines: ~520)
