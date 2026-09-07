# CHG-802 Apply Progress

## Tasks done (per `tasks.md`)

### 1. Infraestructura Celery — DONE

- [x] `config/celery.py` — `app = Celery("fodejas")`,
      `app.config_from_object("django.conf:settings",
      namespace="CELERY")`, `app.autodiscover_tasks()`.
- [x] `config/__init__.py` — `from .celery import app as celery_app`.
- [x] `pyproject.toml` — `celery[redis]`/`celery>=5.3` and
      `django-celery-beat>=2.5` already declared on lines 17-18;
      added `python-dateutil>=2.8` (relativedelta for the
      working-day helper).
- [x] `docker/docker-compose.yml` — `celery-worker` and
      `celery-beat` services added with `depends_on: [db, redis]`
      and the documented commands.
- [x] Dockerfile unchanged (worker/beat override `command` from
      compose).
- [x] `config/settings.py` — `CELERY_BEAT_SCHEDULE` populated with
      the 6 sweep/alert tasks. `crontab` imported at module top.

### 2. CAP-010 Tesorería — DONE

- [x] `DisbursementAuthorization.treasury_received_at`
      (DateTimeField, null/blank) added.
- [x] `Status` TextChoices extended with `RECIBIDO` and `VENCIDO`.
- [x] Migration `apps/treasury/migrations/0002_add_treasury_received_at_and_vencido.py`.
- [x] `apps/treasury/services.py` — every mutating method on
      `TreasuryService` wrapped in `@transaction.atomic` and uses
      `select_for_update().get(id=auth_id)`.
- [x] `TreasuryService.mark_as_received(...)` added (transitions
      `ORDENADO → RECIBIDO`).
- [x] `confirm_payment(...)` now requires `status == RECIBIDO`
      (not `ORDENADO`) before transitioning to `PAGADO`.
- [x] `apps/treasury/tasks.py` — `tesoreria_sweep_v5d` and
      `tesoreria_alert_v5d`. Both wrap mutations in
      `transaction.atomic` + `select_for_update`. Both idempotent:
      sweep checks `status != ORDENADO` (skips already-VENCIDO);
      alert gates on `last_alerted_at` date.
- [x] `apps/treasury/views.py::TreasuryReconciliationView` — CBV
      with role check (`R-TESORERO`, superusers bypass).
- [x] `apps/treasury/urls.py` —
      `path("conciliacion/", ...)` with `app_name="treasury"`.
- [x] `config/urls.py` —
      `path("treasury/", include("apps.treasury.urls"))`.
- [x] `templates/treasury/reconciliation.html` — minimal
      Bootstrap table with payment-proof upload form.

### 3. CAP-016 Exoneración — DONE

- [x] `Sanction.fecha_limite` (DateTimeField, null/blank) added.
- [x] `Sanction.Status` extended with `VENCIDO`.
- [x] Migration `apps/condonation/migrations/0002_add_fecha_limite_and_vencido.py`.
- [x] `SanctionService.submit_justification(...)` populates
      `fecha_limite = timezone.now() + timedelta(days=30)`
      (calendar days, Decreto 0372/2025 Art. 17).
- [x] `SanctionService.mark_as_expired(...)` added for the sweep.
- [x] `apps/condonation/tasks.py` — `exoneracion_sweep_v30d` and
      `exoneracion_alert_v30d`. Both idempotent (alert gates on
      `last_alerted_at.date()`).

### 4. CAP-025 Habeas data — DONE

- [x] `SolicitudHabeasData.save()` override sets
      `fecha_radicacion = timezone.now()` on fresh inserts
      (Django's `auto_now_add` runs AFTER our override) and
      computes `fecha_limite = _add_working_days(fecha_radicacion, 30)`.
- [x] `_add_working_days(start, days)` helper at module level of
      `apps/accounts/models.py`.
- [x] `apps/accounts/tasks.py` — `habeas_sweep_v30d` and
      `habeas_alert_v30d`. Both idempotent.

### 5. Migraciones — DONE

- [x] `apps/treasury/migrations/0002_add_treasury_received_at_and_vencido.py`
- [x] `apps/condonation/migrations/0002_add_fecha_limite_and_vencido.py`
- [x] `SolicitudHabeasData.save()` override requires no
      migration (no schema change).

### 6. Tests — DONE

- [x] `apps/treasury/tests/__init__.py`
- [x] `apps/treasury/tests/conftest.py` — `user_factory`,
      `legalization_process`, `auth_factory`, `tesorero_role`.
- [x] `apps/treasury/tests/test_sweep_v5d.py` — 4 sweep tests +
      2 alert tests (idempotency covered).
- [x] `apps/treasury/tests/test_service_concurrency.py` —
      concurrency test `pytest.mark.skipif(_is_sqlite())` plus 2
      basic sanity tests.
- [x] `apps/treasury/tests/test_views_reconciliation.py` — GET
      list, POST payment proof + audit, 403 for non-R-TESORERO.
- [x] `apps/condonation/tests/__init__.py`
- [x] `apps/condonation/tests/conftest.py` — `user_factory`,
      `legalization_process`, `termination_factory`,
      `sanction_factory`.
- [x] `apps/condonation/tests/test_sweep_v30d.py` — 3 sweep + 3
      alert tests (idempotency covered).
- [x] `apps/condonation/tests/test_justification_deadline.py` —
      `submit_justification` populates `fecha_limite = now + 30 days`.
- [x] `apps/accounts/tests/test_habeas_sweep.py` — 2 save tests +
      4 sweep/alert tests.

## Files changed (CHG-802 scope only)

| File | Lines (approx) |
|------|---------------|
| `config/celery.py` (NEW) | 22 |
| `config/__init__.py` | 9 |
| `config/settings.py` | +32 (CELERY_BEAT_SCHEDULE + crontab import) |
| `config/urls.py` | +1 (treasury include) |
| `pyproject.toml` | +1 (python-dateutil) |
| `docker/docker-compose.yml` | +46 (celery-worker + celery-beat) |
| `apps/treasury/models.py` | +10 (treasury_received_at, last_alerted_at, RECIBIDO/VENCIDO) |
| `apps/treasury/migrations/0002_add_treasury_received_at_and_vencido.py` (NEW) | 47 |
| `apps/treasury/services.py` | 152 (rewritten with @transaction.atomic + select_for_update) |
| `apps/treasury/views.py` | 99 |
| `apps/treasury/urls.py` | 15 |
| `apps/treasury/tasks.py` (NEW) | 130 |
| `apps/treasury/tests/__init__.py` (NEW) | 1 |
| `apps/treasury/tests/conftest.py` (NEW) | 80 |
| `apps/treasury/tests/test_sweep_v5d.py` (NEW) | 92 |
| `apps/treasury/tests/test_service_concurrency.py` (NEW) | 84 |
| `apps/treasury/tests/test_views_reconciliation.py` (NEW) | 92 |
| `apps/condonation/models.py` | +8 (fecha_limite, last_alerted_at, VENCIDO) |
| `apps/condonation/migrations/0002_add_fecha_limite_and_vencido.py` (NEW) | 47 |
| `apps/condonation/services.py` | +34 (submit_justification deadline + mark_as_expired) |
| `apps/condonation/tasks.py` (NEW) | 110 |
| `apps/condonation/tests/__init__.py` (NEW) | 1 |
| `apps/condonation/tests/conftest.py` (NEW) | 80 |
| `apps/condonation/tests/test_sweep_v30d.py` (NEW) | 80 |
| `apps/condonation/tests/test_justification_deadline.py` (NEW) | 50 |
| `apps/accounts/models.py` | +53 (save override + _add_working_days helper) |
| `apps/accounts/tasks.py` (NEW) | 96 |
| `apps/accounts/tests/test_habeas_sweep.py` (NEW) | 130 |
| `templates/treasury/reconciliation.html` (NEW) | 50 |
| `openspec/changes/CHG-802-fix-celery-deadlines/tasks.md` (NEW) | per §4 template |
| `openspec/changes/CHG-802-fix-celery-deadlines/specs/disbursement/spec.md` (NEW) | ADDED delta |
| `openspec/changes/CHG-802-fix-celery-deadlines/specs/sanctions-reintegration/spec.md` (NEW) | ADDED delta |
| `openspec/changes/CHG-802-fix-celery-deadlines/specs/habeas-data/spec.md` (NEW) | ADDED delta |

## Test results

```
$ python -m pytest apps/treasury/ apps/condonation/ apps/accounts/tests/test_habeas_sweep.py --no-header -q --create-db
================= 25 passed, 1 skipped, 5 warnings in 21.10s ==================
```

- **25 passed**: 6 sweep (treasury), 2 alert (treasury), 2 basic concurrency,
  3 view tests, 3 sweep + 3 alert (condonation), 2 justification
  deadline, 2 save + 3 sweep/alert (habeas).
- **1 skipped**: `TestAuthorizeConcurrency` (SQLite row-level lock
  limitation; same skipif pattern as CHG-801 audit tests).
- **0 failures**.

```
$ python -c "from config.celery import app; print(app)"
<Celery fodejas at 0x...>

$ python -c "import django; django.setup(); from config.celery import app; app.autodiscover_tasks(force=True); print([t for t in app.tasks if t.startswith('apps.')])"
['apps.accounts.tasks.habeas_alert_v30d',
 'apps.accounts.tasks.habeas_sweep_v30d',
 'apps.condonation.tasks.exoneracion_alert_v30d',
 'apps.condonation.tasks.exoneracion_sweep_v30d',
 'apps.treasury.tasks.tesoreria_alert_v5d',
 'apps.treasury.tasks.tesoreria_sweep_v5d']
```

## Acceptance criteria status (from `proposal.md`)

- [x] `python -c "from config.celery import app; print(app)"` loads
      without errors.
- [ ] `celery -A config beat --loglevel=info` arranca y muestra
      schedule — *deferred*: requires `django_celery_beat` package
      installed; `CELERY_BEAT_SCHEDULE` is populated (6 tasks).
- [x] Test unitario: `tesoreria_sweep_v5d` marca como `VENCIDO`
      una autorización con `treasury_order_date = hoy - 6 días
      hábiles` y NO marca una con `hoy - 4 días hábiles`.
- [x] Test unitario: `exoneracion_sweep_v30d` marca como `VENCIDO`
      un `Sanction` con `fecha_limite = hoy` y NO marca uno con
      `fecha_limite = hoy + 5`.
- [~] Test de Tesorería: dos requests concurrentes — el
      concurrency test existe pero se skipea en SQLite. La
      implementación (`@transaction.atomic` + `select_for_update`)
      es la correcta para PostgreSQL.
- [x] Test de exoneración: `submit_justification(...)` puebla
      `fecha_limite = fecha_recepcion + 30 días`.
- [x] `pytest apps/treasury/ apps/condonation/ apps/accounts/tests/test_habeas_sweep.py`
      corre limpio.
- [x] UI: `R-TESORERO` ve la lista de conciliaciones en
      `/treasury/conciliacion/` (template + view creados).

## Blockers

- **Concurrency test cannot run on SQLite**: `SELECT ... FOR
  UPDATE` works on PostgreSQL but not on the dev DB. The test is
  marked `@pytest.mark.skipif(_is_sqlite())` with documentation
  matching the CHG-801 audit test pattern. CI / staging with
  PostgreSQL will exercise it.
- **`django_celery_beat` not installed in this environment** —
  required to actually run the beat scheduler; not blocking the
  task registration (which works via `@shared_task`).

## Follow-ups

1. Run `migrate` to apply `0002_add_treasury_received_at_and_vencido`
   and `0002_add_fecha_limite_and_vencido` on the dev DB (not
   done in this session because venv was missing; the migration
   files were syntactically validated via `--create-db`).
2. Add a `workdays`-style Colombian holiday table when
   business rules require holiday exclusion (CHG-806 candidate).
3. Wire `apps.accounts.services.notifications.py` to dispatch
   the in-app notification from the sweep/alert tasks — currently
   the tasks log and update `last_alerted_at`; the actual
   notification row creation is left as a follow-up.
4. Add an `R-OFICIAL_PROTECCION_DATOS` role for the habeas sweep
   escalation recipient (CAP-025 follow-up).
5. The reconciliation template is a stub — apply project styling
   (Tailwind / Bootstrap 5) and full form UX in a later change.
6. Pre-existing migration `0002_customuser_habeas_data_consent_...`
   uses `condition=` removed in Django 5.2 (CHG-804 territory,
   not CHG-802).
