# Proposal: CHG-106-notifications — Infraestructura base de notificaciones (CAP-019)

## Intent

Cerrar CAP-019 (P1, `roadmap.md` §5.1) habilitando la bandeja in-app que ya consume CHG-105 (`habeas.created`, `habeas.expiring_soon`) y que necesitan CAP-002..CAP-030 (criterio de salida Fase 1, `roadmap.md` §5.3).

Decisión vigente (`.kilo/plans/1782491626277-simplificar-roadmap-storage-email.md`, `roadmap.md` §5): **notificaciones exclusivamente in-app**. No email transaccional, no SMS, no push en MVP. El puerto abstracto se diseña igual para no acoplar consumidores a un canal.

## Scope

**In Scope**: `Notification(recipient, event, payload, read_at, created_at)` en `apps/accounts/`; `NotificationPort` abstracto + `InAppNotifier` concreto en `apps/accounts/services/notifications.py`; binding en `apps.py::ready()`; DRF `GET /api/notifications/` (paginado) + `POST /api/notifications/{id}/read/`; admin con acciones masivas (R-ADMIN/R-COORD); Celery `dispatch_notification` asíncrono; reemplazo de `NoopNotifier` dejado por CHG-105.

**Out of Scope**: Email/SMS/Push (roadmap los elimina); plantillas HTML; webhooks; SIC/SNIES; notificaciones a terceros.

## Capabilities

- **New**: `notifications` — `Notification` model + `NotificationPort` + `InAppNotifier` + API REST + admin + tarea Celery.
- **Modified**: `habeas-data` (delta) — `NoopNotifier` reemplazado por `InAppNotifier` vía `ready()`.

## Approach

Patrón **Ports & Adapters**: `NotificationPort.notify(user, event, payload_masked)` en `services/notifications.py`. `InAppNotifier` persiste `Notification` y encola `dispatch_notification.delay()` para no bloquear requests. HTMX bell-icon en `_navbar.html` con badge de no-leídas (placeholder actual en `dashboard.html:106`). PII enmascarada vía `apps/core/logging.py` (CHG-103). Cada notificación registrada en `audit` (CAP-022).

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `apps/accounts/models.py` | New | `Notification` model |
| `apps/accounts/services/notifications.py` | New | `NotificationPort` + `InAppNotifier` |
| `apps/accounts/{serializers,views,urls}.py` | New | API REST list/read |
| `apps/accounts/admin.py` | New | Admin + acciones masivas |
| `apps/accounts/apps.py` | Modified | `ready()` binding del port |
| `apps/accounts/tasks.py` | New | Celery task |
| `templates/accounts/_navbar.html` | New | Bell + badge HTMX |
| `apps/accounts/migrations/0003` | New | Schema |

## Risks

| Risk | Mitigation |
|------|------------|
| Acoplamiento a un canal | `NotificationPort` abstracto; `InAppNotifier` único impl |
| Backpressure en envíos | Celery + Redis broker existente |
| PII en `payload` | Helper `mask_pii()` (CHG-103) en `InAppNotifier` |
| Consumidores no migrados | CHG-105 ya usa `NotificationPort`; idempotente |
| Volumen alto de no-leídas | Índice `(recipient, read_at, created_at)` |

## Rollback Plan

`git revert` en `develop` → `migrate accounts 0002`. `NoopNotifier` queda activo; CHG-105 sigue funcionando. Bandeja UI revierte al placeholder.

## Dependencies

`apps/accounts/User` (CHG-101), `apps/audit/` (CHG-102), `apps/core/logging.py` (CHG-103), Celery+Redis. **Consumidor obligatorio**: CHG-105 (archivado). Habilita CHG-202+ etc.

## Success Criteria

- [ ] `pytest apps/accounts/tests/test_notifications.py` green: create, list, mark-read, mask PII, idempotencia Celery.
- [ ] `GET /api/notifications/` paginado; `POST .../read/` marca `read_at`; 401 sin auth.
- [ ] Admin funcional con acciones masivas (R-ADMIN/R-COORD).
- [ ] Bell-icon HTMX muestra no-leídas (<100ms, cache Redis).
- [ ] CHG-105 `habeas.*` dispara notificaciones reales (no `NoopNotifier`).
- [ ] Cero PII en fixtures/commits/logs; `ruff`/`black`/`isort` clean.
