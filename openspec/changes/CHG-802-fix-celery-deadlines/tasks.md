# Tasks — CHG-802 — Celery + barridos de plazos (Tesorería 5 días, exoneración 30 días, habeas data 30 días hábiles)

## 1. Infraestructura Celery

- [ ] Crear `config/celery.py` con `app = Celery("fodejas")`,
      `app.config_from_object("django.conf:settings", namespace="CELERY")`
      y `app.autodiscover_tasks()`.
- [ ] Modificar `config/__init__.py` para exportar
      `from .celery import app as celery_app`.
- [ ] Confirmar que `pyproject.toml` ya declara `celery>=5.3` y
      `django-celery-beat>=2.5` en `[project].dependencies` (ya
      listados en la línea 17 y 18 del archivo actual). Si faltasen,
      añadirlos; documentar que `workdays` se usará via helper
      interno (`relativedelta` + tabla de festivos) sin agregar
      nueva dep en runtime.
- [ ] Agregar servicios `celery-worker` y `celery-beat` a
      `docker/docker-compose.yml`. Worker con
      `command: celery -A config worker -l info --concurrency 2`.
      Beat con
      `command: celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`.
      Ambos con `depends_on: [db, redis]`.
- [ ] Documentar que `docker/Dockerfile` mantiene `CMD` para gunicorn
      (web); worker/beat sobreescriben `command` en compose (no se
      modifica el Dockerfile en este change).

## 2. CAP-010 — Tesorería (5 días hábiles)

- [ ] Agregar `treasury_received_at = DateTimeField(null=True,
      blank=True)` a `DisbursementAuthorization` en
      `apps/treasury/models.py`.
- [ ] Agregar `VENCIDO = "VENCIDO", "Vencido"` al `Status`
      TextChoices de `DisbursementAuthorization`.
- [ ] Migración `apps/treasury/migrations/0002_add_treasury_received_at_and_vencido.py`.
- [ ] Envolver cada mutación de `TreasuryService` en
      `@transaction.atomic` y recuperar la fila con
      `select_for_update().get(id=auth_id)`:
      `create_authorization`, `authorize`, `send_to_treasury`,
      `confirm_payment`, `reject`.
- [ ] Agregar helper `mark_as_received(auth_id, treasury_user_id)`
      que setea `treasury_received_at = timezone.now()` y
      `status = "RECIBIDO"` (estado nuevo necesario para el flujo
      de "received by Treasury").
- [ ] `confirm_payment` SHALL verificar que la orden está en
      `RECIBIDO` (no solo `ORDENADO`) antes de transicionar a
      `PAGADO`.
- [ ] Crear `apps/treasury/tasks.py` con `tesoreria_sweep_v5d` y
      `tesoreria_alert_v5d` como `@shared_task`. Ambos idempotentes:
      consultan audit log antes de transicionar / notificar para
      evitar doble-firing.
- [ ] Implementar `TreasuryReconciliationView` en
      `apps/treasury/views.py` (CBV `LoginRequiredMixin` +
      `HasRole('R-TESORERO')`). Lista
      `DisbursementAuthorization.objects.filter(status='ORDENADO')
      .order_by('treasury_order_date')` y permite POST con
      `payment_proof` (FileField) llamando a
      `TreasuryService.confirm_payment(...)`.
- [ ] Crear `apps/treasury/urls.py` con
      `path("conciliacion/", TreasuryReconciliationView.as_view(),
      name="reconciliation")`.
- [ ] En `config/urls.py`, agregar
      `path("treasury/", include("apps.treasury.urls"))`.

## 3. CAP-016 — Exoneración (30 días calendario)

- [ ] Agregar `fecha_limite = DateTimeField(null=True, blank=True)`
      a `Sanction` en `apps/condonation/models.py`.
- [ ] Agregar `VENCIDO = "VENCIDO", "Vencido"` al `Status`
      TextChoices de `Sanction`.
- [ ] Migración `apps/condonation/migrations/0002_add_fecha_limite_and_vencido.py`.
- [ ] Modificar `SanctionService.submit_justification(...)` en
      `apps/condonation/services.py` para setear
      `fecha_limite = timezone.now() + timedelta(days=30)` antes
      del `save()` cuando se transiciona a `EN_REVISION`.
- [ ] Agregar helper `mark_as_expired(sanction_id)` para uso del
      sweep task.
- [ ] Crear `apps/condonation/tasks.py` con
      `exoneracion_sweep_v30d` y `exoneracion_alert_v30d` como
      `@shared_task`. Idempotentes.

## 4. CAP-025 — Habeas data (30 días hábiles)

- [ ] Override `SolicitudHabeasData.save()` en
      `apps/accounts/models.py`: si `fecha_limite is None` y
      `fecha_radicacion is not None`, setear
      `fecha_limite = fecha_radicacion + relativedelta(days=30,
      weekdays=True)` (30 días hábiles).
- [ ] Crear `apps/accounts/tasks.py` con `habeas_sweep_v30d` y
      `habeas_alert_v30d` como `@shared_task`. Idempotentes.

## 5. Migraciones

- [ ] `apps/treasury/migrations/0002_add_treasury_received_at_and_vencido.py`
      (campo nuevo + elección TextChoices extendida, ambos
      retro-compatibles — `null=True`, `blank=True`, valor por
      defecto del estado sigue siendo `PENDIENTE`).
- [ ] `apps/condonation/migrations/0002_add_fecha_limite_and_vencido.py`
      (campo nuevo + elección TextChoices extendida).
- [ ] `SolicitudHabeasData.save()` no requiere nueva migración
      (es solo un override Python del método existente).

## 6. Tests

- [ ] `apps/treasury/tests/__init__.py` (paquete vacío).
- [ ] `apps/treasury/tests/conftest.py` con fixtures: `auth_factory`,
      `legalization_process_factory` (datos sintéticos, sin PII).
- [ ] `apps/treasury/tests/test_sweep_v5d.py`:
  - Setup: `DisbursementAuthorization` con `treasury_order_date =
    today - 6 working days`, `status='ORDENADO'`.
  - `tesoreria_sweep_v5d()` debe transicionar a `VENCIDO`.
  - Caso negativo: `today - 4 working days` NO se transiciona.
- [ ] `apps/treasury/tests/test_service_concurrency.py`:
  - Lanzar 2 threads que llaman
    `TreasuryService.authorize(auth_id, user, 'president')`
    simultáneamente.
  - Assert: exactamente uno tiene éxito; el otro lanza
    `ValueError` limpio.
  - Marcar `@pytest.mark.django_db(transaction=True)`.
- [ ] `apps/treasury/tests/test_views_reconciliation.py`:
  - Usuario `R-TESORERO` hace GET a `/treasury/conciliacion/` y ve
    la lista.
  - POST con `payment_proof` transiciona a `PAGADO` y registra
    audit event con `actor=Tesorero`.
- [ ] `apps/condonation/tests/__init__.py` (paquete).
- [ ] `apps/condonation/tests/test_sweep_v30d.py`:
  - `Sanction` con `status='EN_REVISION'`, `fecha_limite = today`.
  - `exoneracion_sweep_v30d()` debe transicionar a `VENCIDO`.
  - Caso negativo: `fecha_limite = today + 5 days` NO se
    transiciona.
- [ ] `apps/condonation/tests/test_justification_deadline.py`:
  - `SanctionService.submit_justification(...)` setea
    `fecha_limite = now + 30 days`.
- [ ] `apps/accounts/tests/test_habeas_sweep.py`:
  - `SolicitudHabeasData` con `fecha_limite = today` se transiciona
    a `vencida`.
  - Caso negativo: `fecha_limite = today + 5 days` no se toca.
  - Verifica que el `save()` calcula `fecha_limite` cuando es
    `None`.

## 7. Pruebas

- [ ] Unitarias:
  - `apps/treasury/tests/test_sweep_v5d.py`.
  - `apps/condonation/tests/test_sweep_v30d.py`.
  - `apps/treasury/tests/test_service_concurrency.py`.
- [ ] Integración:
  - `apps/treasury/tests/test_views_reconciliation.py`.
  - `apps/condonation/tests/test_justification_deadline.py`.
  - `apps/accounts/tests/test_habeas_sweep.py`.
- [ ] Libreta (sanity):
  - `python -c "from config.celery import app; print(app)"` carga
    sin errores.
  - `celery -A config inspect registered` muestra los 6 tasks
    (`tesoreria_sweep_v5d`, `tesoreria_alert_v5d`,
    `exoneracion_sweep_v30d`, `exoneracion_alert_v30d`,
    `habeas_sweep_v30d`, `habeas_alert_v30d`).
- [ ] Regresión: `pytest apps/treasury/ apps/condonation/
  apps/accounts/tests/test_habeas_sweep.py` corre limpio.
