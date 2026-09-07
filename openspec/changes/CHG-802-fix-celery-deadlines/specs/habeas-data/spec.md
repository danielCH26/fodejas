# Delta — CAP-025 Habeas Data (30 días hábiles, Ley 1581/2012 + Decreto 1377/2013)

> Solo bloques delta (ADDED). NO re-establece el spec existente.

## ADDED Requirements

### ADDED — Cálculo automático de `fecha_limite` en `SolicitudHabeasData`

- `SolicitudHabeasData.save()` **SHALL** autocompute
  `fecha_limite` when the field is `None` and `fecha_radicacion`
  is set. The computation **SHALL** be
  `fecha_radicacion + relativedelta(days=30, weekdays=True)`,
  which yields 30 working days (lunes a viernes) per
  Decreto 1377/2013 and Ley 1581/2012. Calendar / holiday
  exclusions beyond weekends are out of scope for this change
  (they require a configurable holiday table, tracked separately).
- The override **SHALL NOT** overwrite an explicitly-set
  `fecha_limite` (i.e. only acts when the field is `None`).
- For fixtures or administrative backfill scenarios where
  `fecha_radicacion` may be `None`, the override **SHALL** be a
  no-op (the deadline is left to the caller).

### ADDED — Plazo de habeas data (CAP-025)

- A periodic Celery task `habeas_sweep_v30d` (Beat schedule:
  daily 09:00 America/Bogota) **SHALL** scan
  `SolicitudHabeasData.objects.filter(estado='radicada',
  fecha_limite__lte=now)` and, for each match, transition
  `estado` to `vencida`, notify the Oficial de Protección de
  Datos, and write an audit event via
  `apps.audit.services.log_audit_event(...)` with `actor=None`
  and the system sentinel `actor_is_system=True`.
- A periodic Celery task `habeas_alert_v30d` (Beat schedule:
  daily 09:00 America/Bogota, fires when the deadline is 5
  working days away) **SHALL** scan
  `SolicitudHabeasData.objects.filter(estado='radicada',
  fecha_limite__lte=now + relativedelta(days=5,
  weekdays=True))` and emit a preventive alert.
- Both tasks **SHALL** be idempotent: re-running them within
  the same day SHALL NOT double-notify or double-transition. The
  audit log provides the guard.
- All audit events emitted by the sweep tasks **SHALL** be
  written through `apps.audit.services.log_audit_event(...)`
  (CHG-801 contract).
