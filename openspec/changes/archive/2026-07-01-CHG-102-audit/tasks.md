# Tasks — CHG-102-audit (CAP-022)

## 1. Model
- [x] Create `AuditEvent` model in `apps/audit/models.py` with all fields
- [x] Add hash calculation helper in models
- [x] Create migration for AuditEvent

## 2. Service
- [x] Implement `log_audit_event()` service in `apps/audit/services.py`
- [x] Implement `calculate_hash()` function
- [x] Implement `verify_chain()` function

## 3. Signals
- [x] Create `apps/audit/signals.py` with post_save and post_delete receivers
- [x] Connect signals to accounts models (User, Role, Permission)
- [x] Connect signals to other domain models
- [x] Register signals in AppConfig

## 4. API
- [x] Create serializers in `apps/audit/serializers.py`
- [x] Create API views in `apps/audit/views.py`
- [x] Register URLs in `apps/audit/urls.py`

## 5. Tests
- [x] Write unit tests for hash calculation
- [x] Write integration tests for signals
- [x] Write API tests for endpoints

## Review Workload Forecast
- Estimated changed lines: 350
- 400-line budget risk: Low
- Single PR recommended

Decision needed before apply: No

## Line Count Estimate
- **Model**: 60 lines
- **Service**: 45 lines
- **Signals**: 40 lines
- **API**: 50 lines
- **Tests**: 120 lines
- **Total**: 315 lines

## Critical Notes
1. All audit writes MUST be atomic (use transaction.atomic())
2. First record's previous_hash = "0" * 64
3. Only append - no updates or deletes on AuditEvent
4. Connect signals in AppConfig.ready() or django.signals.register_signal
