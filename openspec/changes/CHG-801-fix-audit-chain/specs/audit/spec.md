# Spec Delta — CHG-801 Reparar cadena de auditoría CAP-022

> Delta against `openspec/specs/audit/spec.md` (CAP-022).
> This file only contains the delta blocks (ADDED / MODIFIED /
> REMOVED / RENAMED) per AGENTS.md §3 regla 3.

## MODIFIED Requirements

### §3.1 AuditEvent Model (modified)

- The canonical write path SHALL be `apps.audit.services.log_audit_event(...)`.
  Domain services **SHALL NOT** call
  `AuditEvent.objects.create(...)` directly.
- When `actor` is `None` (signal outside an HTTP request, management
  command, or background task without an authenticated user), the
  helper SHALL mark the event with the metadata sentinel
  `actor_is_system=True` so that downstream verifiers can distinguish
  system actions from user actions.
- The `AuditEvent` model SHALL NOT be mutated from view code. All
  writes SHALL go through `services.log_audit_event(...)`. Direct
  `AuditEvent.save()` from view layer SHALL raise
  `RuntimeError` when the
  `AUDIT_FORCE_SERVICES_ONLY` Django setting is `True` (default in
  production).

### §3.2 Hash Chain (modified)

- The current hash SHALL be calculated within a single transaction
  that takes a `SELECT ... FOR UPDATE` lock on the chain head
  (most recent `AuditEvent` ordered by `timestamp DESC`). The helper
  SHALL acquire the lock inside `@transaction.atomic`.
- The previous-hash lookup SHALL be:
  `AuditEvent.objects.select_for_update().order_by("-timestamp").first()`.
- Concurrent writers SHALL serialize through this lock; the helper
  SHALL raise `AuditChainLockError` if the lock cannot be acquired
  in the configured timeout (default 5 seconds).
- The chain SHALL remain verifiable after any sequence of successful
  writes: `verify_chain()` SHALL return `is_valid=True` for the
  full event set.

### §3.3 Automatic Logging (modified)

- `AuditConfig.ready()` SHALL invoke `register_audit_signals()`
  exactly once when the app is loaded.
- `register_audit_signals()` SHALL connect `post_save` and
  `post_delete` to `audit_save_receiver` and
  `audit_delete_receiver` for every `(ModelClass, "module")` tuple
  in `AUDIT_MODELS`. The match SHALL use class identity (`sender is
  ModelClass`), not string comparison, so that subclasses of
  `Model` are correctly excluded.
- `audit_save_receiver` and `audit_delete_receiver` SHALL resolve
  the current actor from
  `apps.core.logging_config.get_actor()` (a `ContextVar`
  populated by `RequestIDMiddleware`). When no actor is available,
  the helper SHALL be called with `actor=None` and the metadata
  SHALL carry `actor_is_system=True`.
- Audit signal handlers SHALL NOT swallow exceptions silently.
  Failures SHALL be logged via
  `apps.core.logging_config.logger.exception(...)` with the
  request id and entity metadata.

### §3.4 Audit API (modified)

- `AuditEventListView` SHALL require `IsAuditViewer` (from
  `apps.accounts.permissions`) on the API endpoint
  `/api/audit/events/`. `R-ASPIRANTE` and unauthenticated clients
  SHALL receive `HTTP 403` and `HTTP 401` respectively.
- `AuditEventDetailView` SHALL apply the same permission.
- `AuditChainVerifyView` SHALL retain `IsAdminUser` (only
  administrators may trigger verification).

### §3.5 Retention (unchanged)

- No change: 20 years (project.md §13.3).

## ADDED Requirements

### §3.6 Actor contextvar

- The platform SHALL expose
  `apps.core.logging_config.actor_var: ContextVar[CustomUser | None]`
  (with helpers `get_actor()` and `set_actor(user)`) so that
  downstream code — including audit signals — can read the current
  request user without an explicit request object.
- `RequestIDMiddleware` SHALL set `actor_var` to `request.user`
  when the request has an authenticated user, and SHALL reset
  `actor_var` to `None` after the response is returned (to prevent
  leakage between requests on the same worker thread).
- When `actor_var` is `None` at audit-write time, the audit helper
  SHALL propagate `actor=None` and set `actor_is_system=True` in
  the event metadata.

### §3.7 Direct-write regression

- The repository SHALL NOT contain any occurrence of
  `AuditEvent.objects.create(...)` in `apps/` outside of
  `apps/audit/services.py`. The CI SHALL enforce this with
  `grep -r "AuditEvent.objects.create" apps/ | grep -v
  apps/audit/services.py` returning empty.
