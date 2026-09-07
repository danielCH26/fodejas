# Delta — CAP-016 Sanctions & Reintegration (Exoneración 30 días calendario)

> Solo bloques delta (ADDED). NO re-establece el spec existente.

## ADDED Requirements

### ADDED — Plazo de exoneración (30 días calendario, Decreto 0372/2025 Art. 17)

- The `Sanction` entity **SHALL** carry a
  `fecha_limite: DateTimeField(null=True, blank=True)` field.
- The `Sanction.Status` enumeration **SHALL** include the value
  `VENCIDO`.
- `SanctionService.submit_justification(...)` **SHALL** populate
  `fecha_limite = timezone.now() + timedelta(days=30)` (30
  calendar days, NOT working days) at the moment the sanction
  transitions to `EN_REVISION`.
- A periodic Celery task `exoneracion_sweep_v30d` (Beat
  schedule: daily 09:00 America/Bogota) **SHALL** scan
  `Sanction.objects.filter(status='EN_REVISION',
  fecha_limite__lte=now)` and, for each match, transition to
  `VENCIDO`, notify the applicant and the reviewer, and write an
  audit event via
  `apps.audit.services.log_audit_event(...)` with `actor=None`
  and the system sentinel `actor_is_system=True`.
- A periodic Celery task `exoneracion_alert_v30d` (Beat
  schedule: daily 09:00 America/Bogota, fires when the deadline
  is 5 days away) **SHALL** scan
  `Sanction.objects.filter(status='EN_REVISION',
  fecha_limite__lte=now + timedelta(days=5))` and emit a
  preventive alert.
- Both tasks **SHALL** be idempotent: re-running them within
  the same day SHALL NOT double-notify or double-transition. The
  audit log provides the guard.
- All audit events emitted by the sweep tasks and by
  `SanctionService` mutations **SHALL** be written through
  `apps.audit.services.log_audit_event(...)` (CHG-801 contract).
