# CHG-802 — Celery + barridos de plazos (Tesorería 5 días, exoneración 30 días)

## Contexto

La auditoría completa del 2026-09-05 (`docs/audits/extended-audit.md`
AUD-016 BLOCKER + AUD-004, AUD-013, AUD-022, AUD-023) detectó que **no
existe infraestructura Celery** en el proyecto:

- No hay `config/celery.py`.
- No hay `apps/*/tasks.py`.
- Cero `@shared_task` / `@periodic_task` / `beat_schedule` en todo
  el repo.
- `apps/treasury/services.py` muta `DisbursementAuthorization` con
  `save()` plano, sin `transaction.atomic` ni `select_for_update`.
- `apps/treasury/views.py` y `apps/treasury/urls.py` están vacíos
  (0 bytes) — Tesorería no tiene UI de conciliación.
- `apps/condonation/models.py` no tiene campos `fecha_recepcion` ni
  `fecha_limite` en `Sanction`.

`roadmap.md:354` promete "El sistema respeta el plazo de 5 días hábiles
de Tesorería y emite alertas si se vence" y `roadmap.md:395` promete
"solicitud de exoneración se resuelve en 30 días calendario". Ambos
incumplidos.

AGENTS.md §6 regla 5 ("no saltarse pruebas en reglas monetarias o de
plazos") y §6 regla 7 (no inventar plazos — Decreto 0372/2025:
Tesorería 5 días hábiles, exoneraciones 30 días calendario) están
violados a nivel plataforma.

## Capacidades afectadas

- **CAP-010** (Autorización de pago / Tesorería, `project.md` §8).
- **CAP-016** (Sanciones, reintegros, exoneraciones, `project.md` §8).
- **CAP-025** (Habeas data 30 días hábiles — heredada del design
  archivado de CHG-105 que nunca aterrizó).

## Reglas de negocio afectadas

- `AGENTS.md` §6 regla 5 (plazos normativos requieren prueba).
- `AGENTS.md` §6 regla 7 (Decreto 0372/2025 plazos exactos).
- `project.md` §11 (reglas de negocio CAP-010 y CAP-016).
- `roadmap.md` §7 Entregables verificables (5 días hábiles
  Tesorería, 30 días calendario exoneración).

## Cambios propuestos

### Delta en `specs/disbursement/spec.md` y `specs/sanctions-reintegration/spec.md`

#### ADDED — CAP-010 § Plazo de Tesorería

`DisbursementAuthorization` **SHALL** tener un campo
`treasury_received_at: DateTimeField(null=True)` que se setea cuando
Tesorería marca la orden como recibida (paso previo al pago). Un
periodic task `tesoreria_sweep_v5d` (celery beat, diario 09:00
America/Bogota) **SHALL** ejecutar:

```
SELECT id FROM treasury_disbursementauthorization
WHERE status = 'ORDENADO'
  AND treasury_order_date <= (current_date - 5 working days)
```

Para cada resultado, transicionar a `VENCIDO`, notificar a la
Coordinación Técnica y emitir un audit event. Un task gemelo
`tesoreria_alert_v5d` (diario 08:00) **SHALL** alertar 1 día antes
del vencimiento.

#### ADDED — CAP-010 § UI de conciliación

`apps/treasury/views.py` **SHALL** implementar
`TreasuryReconciliationView` que lista
`DisbursementAuthorization.objects.filter(status='ORDENADO')` y
permite a Tesorería adjuntar `payment_proof` (FileField) y llamar
`TreasuryService.confirm_payment(...)`.

#### ADDED — CAP-016 § Plazo de exoneración

`Sanction` **SHALL** tener un campo `fecha_limite: DateTimeField`
auto-poblado en `submit_justification(...)` como
`fecha_recepcion + relativedelta(days=30)`. Un periodic task
`exoneracion_sweep_v30d` (diario 09:00) **SHALL** escanear
`Sanction.objects.filter(status='EN_REVISION', fecha_limite__lte=now)`
y marcar `VENCIDO`, notificar al solicitante y al reviewer.
`exoneracion_alert_v30d` (día 25) **SHALL** alertar preventivamente.

#### ADDED — CAP-025 § Plazo de Habeas data

`SolicitudHabeasData` **SHALL** autocompletar `fecha_limite` en
`save()` como `fecha_radicacion + relativedelta(days=30, weekdays=True)`
(30 días hábiles, no naturales, según Decreto 1377/2013 y Ley 1581/2012).
Un periodic task `habeas_sweep_v30d` (diario 09:00) **SHALL** escanear
`SolicitudHabeasData.objects.filter(status='PENDIENTE',
fecha_limite__lte=now)` y notificar al responsable + escalar al
Oficial de Protección de Datos. `habeas_alert_v30d` (día 25)
**SHALL** alertar preventivamente.

### Cambios concretos

1. **Infraestructura Celery** (nuevo):
   - `config/celery.py` — `app = Celery("fodejas")`,
     `app.config_from_object("django.conf:settings",
     namespace="CELERY")`, `app.autodiscover_tasks()`.
   - `config/__init__.py` — `from .celery import app as celery_app`.
   - `pyproject.toml` — agregar `celery[redis]` y
     `django-celery-beat` como deps.
   - `docker/docker-compose.yml` — agregar servicio `celery-worker`
     y `celery-beat`.
   - `docker/Dockerfile` — `CMD` separado para worker vs web (CMD
     se sobreescribe en compose).
2. **CAP-010 Tesorería**:
   - `apps/treasury/models.py` — agregar
     `treasury_received_at`, estado `VENCIDO` en `Status`.
   - `apps/treasury/services.py` — envolver cada mutación en
     `@transaction.atomic` + `select_for_update` al recuperar
     `DisbursementAuthorization`.
   - `apps/treasury/tasks.py` (nuevo) — `tesoreria_sweep_v5d`,
     `tesoreria_alert_v5d`.
   - `apps/treasury/views.py` — `TreasuryReconciliationView`
     (CBV, LoginRequiredMixin, `R-TESORERO` permission).
   - `apps/treasury/urls.py` — wire a las vistas.
   - `config/urls.py` — `include("apps.treasury.urls")`.
3. **CAP-016 Exoneración**:
   - `apps/condonation/models.py` — agregar
     `Sanction.fecha_limite: DateTimeField(null=True)` + estado
     `VENCIDO`.
   - `apps/condonation/services.py` — `submit_justification(...)`
     calcula `fecha_limite = timezone.now() + timedelta(days=30)`.
   - `apps/condonation/tasks.py` (nuevo) — `exoneracion_sweep_v30d`,
     `exoneracion_alert_v30d`.
4. **CAP-025 Habeas data** (extensión):
   - `apps/accounts/models.py` — `SolicitudHabeasData.save()`
     override que setea `fecha_limite = fecha_radicacion +
     relativedelta(days=30, weekdays=True)`.
   - `apps/accounts/tasks.py` (nuevo) — `habeas_sweep_v30d`,
     `habeas_alert_v30d`.
5. **Migración**:
   - `apps/treasury/migrations/XXXX_add_treasury_received_at_and_vencido.py`.
   - `apps/condonation/migrations/XXXX_add_fecha_limite_and_vencido.py`.

## Criterios de aceptación

- [ ] `python -c "from config.celery import app; print(app)"` carga
      sin errores.
- [ ] `celery -A config beat --loglevel=info` arranca y muestra
      schedule con `tesoreria_sweep_v5d` y `exoneracion_sweep_v30d`.
- [ ] Test unitario: `tesoreria_sweep_v5d` marca como `VENCIDO` una
      autorización con `treasury_order_date = hoy - 6 días hábiles`
      y NO marca una con `hoy - 4 días hábiles`.
- [ ] Test unitario: `exoneracion_sweep_v30d` marca como `VENCIDO`
      un `Sanction` con `fecha_limite = hoy` y NO marca uno con
      `fecha_limite = hoy + 5`.
- [ ] Test de Tesorería: dos requests concurrentes a
      `authorize(...)` con la misma `auth_id` → uno gana, el otro
      recibe `ValueError` limpio (sin doble autorización).
- [ ] Test de exoneración: `submit_justification(...)` puebla
      `fecha_limite = fecha_recepcion + 30 días` sin intervención
      manual.
- [ ] `pytest apps/treasury/ apps/condonation/ apps/audit/`
      corre limpio (incluyendo las nuevas tareas).
- [ ] UI: `R-TESORERO` ve la lista de conciliaciones en
      `/treasury/conciliacion/`.

## Pruebas

- Unitarias:
  - `apps/treasury/tests/test_sweep_v5d.py`.
  - `apps/condonation/tests/test_sweep_v30d.py`.
  - `apps/treasury/tests/test_service_concurrency.py`.
- Integración:
  - `apps/treasury/tests/test_views_reconciliation.py` — flujo
    completo Tesorería: ver lista → subir comprobante → marcar
    pagado → audit event con actor=Tesorero.
  - `apps/condonation/tests/test_justification_deadline.py` —
    submit_justification setea fecha_limite; sweep la respeta.
- Libreta:
  - `pytest -k "celery_app"` verifica carga y registro de tasks.

## Riesgos y Fuera del alcance

- **Riesgo**: tareas Celery corriendo en staging sin base de datos de
  staging limpia podrían transicionar datos reales. Mitigación:
  flags de entorno `RUN_DEADLINE_SWEEPS_IN_TESTS=False` y
  comandos management `cancel_sweep` para rollback manual.
- **Riesgo**: el cálculo de "5 días hábiles" requiere calendario
  colombiano (festivos). Usar `workdays` lib + tabla de festivos
  parametrizable; no hardcodear.
- **Fuera del alcance**:
  - No se rediseña la UI de Tesorería (estilo CSS).
  - No se agrega Celery para notificaciones (queda para CHG-501).
  - No se migra el historial de autorizaciones previas.

## Referencias

- `docs/audits/extended-audit.md` §2, §8.1 AUD-016, §5.6, §6.4.
- `roadmap.md` §7 Entregables verificables, §8 §8.2.
- `AGENTS.md` §6 reglas 5 y 7.
- Decreto 0372/2025 (Art. 2 para Tesorería; Art. 17 para
  exoneraciones — pendiente confirmar en CHG-806).
