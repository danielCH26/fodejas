# Design: CHG-106-notifications — Infraestructura base de notificaciones (CAP-019)

## Technical Approach

Ports & Adapters per proposal §Approach. `NotificationPort` is a
`typing.Protocol` (not an ABC) in `apps/accounts/services/notifications.py`;
`InAppNotifier` is the sole concrete adapter, persisting `Notification`
rows. `apps/accounts/apps.py::ready()` binds a module-level registry
`NOTIFIERS = [InAppNotifier()]` (spec scenario "Despacho a múltiples
adapters"). A Celery `dispatch_notification` task decouples the audit
hash-chain write (`notification.dispatched`) from the request path.
API is DRF + JWT, owner-scoped. Audit dotted events and `mask_pii`
are prerequisites CHG-105 designed but never landed — CHG-106 includes
the minimal versions (see Open Questions).

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|---|---|---|---|
| Port shape | `typing.Protocol` + registry list | ABC subclassing | Multi-adapter dispatch (spec) without forcing inheritance; `ready()` swaps impl |
| Idempotency | `created_date` DateField + `UniqueConstraint(recipient,event,created_date)` | Postgres expr index on `date(created_at)` | Portable, queryable; spec "mismo día UTC → no duplicado, `payload.repeat_count`++" |
| Async dispatch | `dispatch_notification.delay(id)` sets `dispatched_at` | Inline audit write | Keeps hash-chain DB write off hot path; broker-down doesn't lose the notification (spec "Falla de broker no rompe creación") |
| `leido` | `@property` from `read_at` | Stored bool | Spec: "derivado de `read_at`"; `?leido=false` → `read_at__isnull=True` |
| Pagination | custom `NotificationPagination` (20/100) | DRF default (20, no max) | Spec "default 20, max 100" |
| Admin RBAC | `has_permission` checks `UserRole.role.code ∈ {R-ADMIN,R-COORD}` | `IsAdminUser` (superuser-only) | Spec "R-CT → 403"; matches `SolicitudHabeasDataAdmin` pattern |
| `mask_pii` | create `apps/core/logging.py::mask_pii` here | Inline in notifier | Proposal cites "CHG-103" but CHG-103 was catalogs; helper never built — cross-cutting util belongs in core |
| Audit dotted actions | widen `action` 20→40 + `notification.*` choices here (`audit/0003`) | Defer to CHG-105 | CHG-105's `audit/0003` never landed; `notification.dispatch_failed` (27 chars) can't fit CharField(20) |
| Celery bootstrap | create `config/celery.py` + `config/__init__.py` import here | Defer | settings has `CELERY_BROKER_URL` but no Celery app; task can't run without it |

## Data Flow

```
Consumer (habeas view) ──notify(user,event,payload)──▶ NotificationPort
                                                            │
                                                            ▼
                                              InAppNotifier.notify()  (atomic)
                                  ┌──────────────────────────┼─────────────────────────┐
                                  ▼                          ▼                         ▼
                          mask_pii(payload)        Notification upsert           audit.log_audit_event(
                                  │               (idempotent by UTC day;        "notification.created")
                                  │                repeat_count++ on dup)              │
                                  ▼                          │                         │
                          (return to caller ◀────────────────┘                         │
                           — non-blocking)                                              │
                                  │                                                     │
                                  ▼                                                     ▼
                       dispatch_notification.delay(id) ──▶ Celery worker ──▶ audit("notification.dispatched")
                                                                    │             + dispatched_at=now()
                                                                    └──▶ invalidate Redis unread cache

DRF /api/notifications/ ──▶ owner queryset ──▶ unread_count (Redis-cached 30s) ──▶ HTMX bell badge
```

## Interfaces / Contracts

```python
# apps/accounts/services/notifications.py
class NotificationPort(Protocol):
    def notify(self, user: CustomUser, event: str, payload: dict) -> "Notification": ...
    def mark_read(self, notification: "Notification", user: CustomUser) -> None: ...

NOTIFIERS: list[NotificationPort] = []  # bound in apps.ready()

def get_notifiers() -> list[NotificationPort]:
    return NOTIFIERS

class InAppNotifier:
    def notify(self, user, event, payload): ...      # masks, upserts, delay(), audit
    def mark_read(self, notification, user): ...     # ownership check, read_at=now()
```

Idempotency upsert (non-obvious):

```python
# InAppNotifier.notify — inside transaction.atomic()
today = timezone.now().date()  # UTC (USE_TZ)
obj, created = Notification.objects.select_for_update().get_or_create(
    recipient=user, event=event, created_date=today,
    defaults={"tipo": tipo, "titulo": titulo, "mensaje": mensaje,
              "payload": mask_pii(payload), "repeat_count": 1},
)
if not created:
    obj.repeat_count = F("repeat_count") + 1
    obj.save(update_fields=["repeat_count"])
# then: log_audit_event("notification.created", ...) ; dispatch_notification.delay(obj.id)
```

## File Changes

| File | Action | Description |
|---|---|---|
| `apps/accounts/models.py` | Modify | Add `Notification` (UUID PK, `recipient` FK CASCADE, `event` CharField(64), `tipo` TextChoices info/warning/success/error, `titulo`(140), `mensaje` TextField, `payload` JSONField, `read_at` nullable, `created_at` auto, `created_date` for idempotency, `dispatched_at` nullable, `repeat_count` int default 1) + `leido` property |
| `apps/accounts/migrations/0003_notification.py` | Create | table + index `(recipient, read_at, -created_at)` + unique `(recipient, event, created_date)` |
| `apps/accounts/services/__init__.py` | Create | package (none exists) |
| `apps/accounts/services/notifications.py` | Create | `NotificationPort`, `InAppNotifier`, `NOTIFIERS`, `get_notifiers()` |
| `apps/accounts/apps.py` | Modify | `ready()` sets `NOTIFIERS=[InAppNotifier()]` |
| `apps/accounts/api/serializers.py` | Modify | `NotificationSerializer` (excludes `payload` raw; exposes `leido`) |
| `apps/accounts/api/views.py` | Modify | `NotificationViewSet` (list/retrieve/read/read-all/unread_count) + replace habeas `# TODO: send notification` with `get_notifiers()→notify()` |
| `apps/accounts/api/urls.py` | Modify | register `notifications` |
| `apps/accounts/admin.py` | Modify | `NotificationAdmin` (R-ADMIN/R-COORD only) + `marcar_como_leida`/`reenviar_a_audit` actions |
| `apps/accounts/tasks.py` | Create | `dispatch_notification` shared_task (idempotent on `dispatched_at`, `autoretry_for=(TransientError,)`, `max_retries=3`, `retry_backoff=True`), `on_failure` → audit `notification.dispatch_failed` |
| `apps/core/logging.py` | Create | `mask_pii(value, kind=None)` helper (proposal's "CHG-103" ref is stale) |
| `apps/audit/models.py` | Modify | `action` 20→40, `ACTION_CHOICES` += `notification.created/dispatched/dispatch_failed/access_denied` |
| `apps/audit/migrations/0003_alter_action_*` | Create | `AlterField` on `action` (reversible; no data rows use dotted yet) |
| `config/celery.py` | Create | `Celery("fodejas")`, `autodiscover_tasks(["apps.accounts"])` |
| `config/__init__.py` | Modify | `from .celery import app as celery_app` |
| `templates/accounts/_notifications_bell.html` | Create | HTMX partial: bell + badge, `hx-get="/api/notifications/unread_count/"` `hx-trigger="load, every 60s"` |
| `templates/base.html` | Modify | include bell partial in navbar (navbar is inline here, not `_navbar.html`) |
| `apps/accounts/tests/test_notifications.py` | Create | model, port dispatch, idempotency, mask, API 401/403, read-all idempotent, admin RBAC, task idempotency/backoff |

> Note: no `apps/accounts/services/habeas_data.py` exists (CHG-105 service
> never landed), so habeas notify-calls are wired in the existing views'
> `# TODO` sites, not a service layer.

## API Endpoints

| Method | Path | Behavior |
|---|---|---|
| GET | `/api/notifications/` | paginated 20 (max 100), `?leido=true|false`, owner-scoped (`recipient=request.user`) |
| POST | `/api/notifications/{id}/read/` | set `read_at=now()` if owner else 403 (+ audit `notification.access_denied`) |
| POST | `/api/notifications/read-all/` | mark all pending; idempotent `{updated: N}` |
| GET | `/api/notifications/unread_count/` | `{unread: N}` Redis-cached 30s for the HTMX badge |

## Admin Configuration

`NotificationAdmin`: `list_display=(recipient, event, tipo, leido, created_at)`,
`list_filter=(tipo, event, leido, created_at)`, `date_hierarchy=created_at`,
`search_fields=(recipient__email, event, titulo)`,
`readonly_fields=(payload, created_at, dispatched_at, repeat_count)`.
`has_permission` → `request.user.user_roles.filter(role__code__in=["R-ADMIN","R-COORD"]).exists()`.
Actions: `marcar_como_leida` (bulk `read_at=now()`, audit batch),
`reenviar_a_audit` (re-emit `notification.dispatched`).

## Celery Task Design

`@shared_task(bind=True, max_retries=3, autoretry_for=(TransientError,),
retry_backoff=True, retry_backoff_max=60, retry_jitter=True)
def dispatch_notification(self, notification_id)`:
1. load `Notification`; if `dispatched_at` → return (idempotent, spec scenario).
2. `log_audit_event(action="notification.dispatched", entity="Notification", entity_id=notification_id, module="accounts")`.
3. set `dispatched_at=now()`, save.
4. invalidate Redis `unread:{user_id}` cache key.
5. `on_failure(self, exc, ...)`: after retries exhausted → audit `notification.dispatch_failed`.

`TransientError(Exception)` defined in `tasks.py` (audit DB write failure).
`apps/core/celery_metrics.py` already instruments `task_prerun/postrun`.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | `mask_pii` rules (doc/telefono/email → `***123`); `Notification` defaults; `leido` property; port dispatches to all registered notifiers | pure funcs + model tests |
| Unit | `InAppNotifier.notify`: masks payload, upserts idempotent (`repeat_count`++), emits `notification.created`; broker `ConnectionError` → still created + audit `notification.dispatch_failed` | `transaction.atomic`, `freezegun` (day boundary), patch `.delay` to raise |
| Integration | `GET/POST /api/notifications/` paginated, owner-scoped, 401 (no token), 403 (other's `read/`), `read-all/` idempotent `{updated:0}` | `APIClient` + JWT + factories |
| Integration | Admin: R-ADMIN/R-COORD allowed; R-CT → 403 + audit `permission_denied`; `marcar_como_leida` bulk | `AdminClient` + role factories |
| Task | `dispatch_notification` double-run no re-emit; `TransientError` backoff 3 then `notification.dispatch_failed` | `CELERY_TASK_ALWAYS_EAGER`, patch `log_audit_event` to raise |

## Migration / Rollout

New: `accounts/0003_notification`, `audit/0003_alter_action` (reversible
`AlterField`; no dotted rows exist yet), `config/celery.py`. No data
migration (no notifications yet). Rollback: `git revert` + `migrate
accounts 0002` + `migrate audit 0002`; `NOTIFIERS` resets to `[]`
(`get_notifiers()` no-ops; habeas views stay green). No feature flag.

## Open Questions

- [ ] **`mask_pii` provenance**: proposal cites "CHG-103 `apps/core/logging.py`" but CHG-103 was *catalogs*; no `logging.py`/`mask_pii` exists (grep-confirmed). Confirm: create `mask_pii` in CHG-106 (this design's choice) or split a dedicated infra CHG first?
- [ ] **Audit dotted actions**: `action` is `CharField(20)` with 6 base choices; `notification.dispatch_failed` (27 chars) can't fit. CHG-105's proposed `audit/0003` (widen→40 + dotted) never landed. Confirm CHG-106 includes the audit extension, or block on a prerequisite CHG?
- [ ] **Celery bootstrap**: no `config/celery.py` / empty `config/__init__.py` (settings only sets broker URL). Confirm CHG-106 bootstraps Celery, or dedicated infra CHG first?
- [ ] **NoopNotifier replacement**: no `NoopNotifier` exists in code (grep-confirmed; CHG-105 archived at spec, views have only `# TODO: send notification`). Confirm scope: CHG-106 implements the real port + wires habeas views' TODOs, with no literal NoopNotifier deletion.
- [ ] **Bell UI host**: proposal cites "placeholder at `dashboard.html:106`" but no `dashboard.html` exists; navbar is inline in `base.html`. Confirm: add bell as a partial included in `base.html`, or defer to a UI CHG?
- [ ] **Idempotency field**: `created_date` DateField + unique constraint (this design) vs Postgres expression index on `date(created_at)` — confirm preferred.
