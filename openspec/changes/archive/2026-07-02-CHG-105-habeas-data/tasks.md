# Tasks — CHG-105-habeas-data

## Review Workload Forecast
- Estimated lines: 350
- Risk assessment: Below 400-line threshold (low risk for single PR)

## 1. Models
- [x] Create Consentimiento model in apps/accounts/models.py
- [x] Create SolicitudHabeasData model in apps/accounts/models.py
- [x] Add habeas_data_consent field to CustomUser

## 2. API
- [x] Add serializers in apps/accounts/api/serializers.py
- [x] Add views in apps/accounts/api/views.py

## 3. Admin
- [x] Add ConsentimientoAdmin in apps/accounts/admin.py
- [x] Add SolicitudHabeasDataAdmin in apps/accounts/admin.py

## 4. Migration
- [x] Generate migration (0002)
- [x] Apply migration

## 5. Testing
- [x] Add tests for Consentimiento in apps/accounts/tests/test_models.py
- [x] Add tests for SolicitudHabeasData in apps/accounts/tests/test_models.py
- [x] All 94 tests passing

## Implementation Notes
- Consentimiento: version tracking with SHA-256 hash, IP logging
- SolicitudHabeasData: ARCO types (consulta, rectificacion, actualizacion, supresion)
- 30-day deadline tracking with fecha_limite field
- Estado transitions: radicada -> en_tramite -> resuelta/rechazada/vencida

## Dependencies
- CAP-001 (auth): complete
- CAP-022 (audit): complete
- CAP-019 (notifications): deferred (uses NoopNotifier placeholder)
