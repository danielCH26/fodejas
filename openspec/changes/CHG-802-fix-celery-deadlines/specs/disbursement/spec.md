# Delta — CAP-010 Disbursement (Tesorería 5 días hábiles)

> Solo bloques delta (ADDED). NO re-establece el spec existente.

## ADDED Requirements

### ADDED — Plazo de Tesorería (5 días hábiles, Decreto 0372/2025 Art. 2)

- The `DisbursementAuthorization` entity **SHALL** carry a
  `treasury_received_at: DateTimeField(null=True)` field. This
  field is populated when Treasury marks the order as received
  (intermediate step before `PAGADO`).
- The `DisbursementAuthorization.Status` enumeration **SHALL**
  include the value `VENCIDO`. Transitions to `VENCIDO` are
  performed only by the periodic sweep task (not by Treasury).
- A periodic Celery task `tesoreria_sweep_v5d` (Beat schedule:
  daily 09:00 America/Bogota) **SHALL** scan
  `DisbursementAuthorization.objects.filter(status='ORDENADO',
  treasury_order_date <= (current_date - 5 working days))` and,
  for each match, transition the row to `VENCIDO`, emit a
  notification to Coordinación Técnica, and write an audit event
  via `apps.audit.services.log_audit_event(...)` with
  `actor=None` and the system sentinel
  `actor_is_system=True`.
- A periodic Celery task `tesoreria_alert_v5d` (Beat schedule:
  daily 08:00 America/Bogota) **SHALL** scan
  `DisbursementAuthorization.objects.filter(status='ORDENADO',
  treasury_order_date <= (current_date - 4 working days))` and
  emit a preventive notification.
- Both tasks **SHALL** be idempotent: re-running them within the
  same day SHALL NOT double-notify or double-transition. The
  `last_alerted_at` denormalized field on
  `DisbursementAuthorization` (added together with the deadline
  fields) and the audit log together provide the guard.

### ADDED — Concurrencia transaccional (CAP-010)

- Every method on `TreasuryService` that mutates a
  `DisbursementAuthorization` (`create_authorization`,
  `authorize`, `send_to_treasury`, `confirm_payment`, `reject`)
  **SHALL** be wrapped in `@transaction.atomic` and **SHALL**
  retrieve the row via
  `DisbursementAuthorization.objects.select_for_update()
  .get(id=auth_id)` before mutating.
- When two concurrent calls reach `authorize(auth_id, ...)`
  with the same role, exactly one **SHALL** succeed; the other
  **SHALL** raise `ValueError` with a clear message (no double
  authorization, no silent overwrite).

### ADDED — UI de conciliación manual (CAP-010)

- `apps.treasury.views.TreasuryReconciliationView` **SHALL**
  implement a class-based view restricted to authenticated users
  holding the `R-TESORERO` role.
- The view **SHALL** list
  `DisbursementAuthorization.objects.filter(status='ORDENADO')
  .order_by('treasury_order_date')` (oldest first) and **SHALL**
  accept a `POST` with a `payment_proof` `FileField`. On valid
  POST, the view delegates to
  `TreasuryService.confirm_payment(...)` which transitions to
  `PAGADO` only if the prior state is `RECIBIDO`.
- The URL `/treasury/conciliacion/` **SHALL** route to this
  view, registered via `apps.treasury.urls`.
- All audit events emitted by this view **SHALL** be written
  through `apps.audit.services.log_audit_event(...)` with
  `actor=request.user` (CHG-801 contract).
