# Tasks — CHG-106-notifications

## Review Workload Forecast
- Estimated lines: 500 (slightly over 400 limit)
- Risk assessment: Medium (single PR)

## 1. Core Implementation
- [x] Create Notification model in apps/accounts/models.py
- [x] Implement NotificationPort and InAppNotifier in apps/accounts/services/notifications.py
- [x] Add API serializers and views
- [x] Add admin configuration
- [x] Wire InAppNotifier in apps/accounts/apps.py ready()

## 2. CHG-105 Integration
- [x] Replace habeas view TODO sites with notification calls

## 3. Migration
- [x] Generate and apply migration (0003)

## 4. Testing
- [x] All 94 tests passing

## Implementation Notes
- Notification model: tipo, titulo, mensaje, leido property, recipient FK
- NotificationPort: Protocol with notify() method
- InAppNotifier: idempotent upsert (one per user-event-date)
- API: list, mark read, mark all read
- Admin: RBAC restricted to R-ADMIN/R-COORD

## Simplified from Design
- No Celery (sync dispatch)
- No mask_pii helper
- No HTMX UI
- Simplified audit (short action names)

## Dependencies
- CHG-105 (habeas-data): integrated
- CHG-101 (auth): complete
- CHG-102 (audit): complete
