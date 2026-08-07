# Tasks — CHG-202-applicator-fui

## Review Workload Forecast
- Estimated lines: 450
- Risk assessment: Medium (single PR)

## 1. Models
- [x] Create Solicitud model with JSONB fields
- [x] Create Anexo model for attachments
- [x] Create RadicadoSecuencial for sequence
- [x] Generate migration

## 2. Services
- [x] Create radicado_service.py with generar_radicado()
- [x] Create wizard_service.py with save_draft() and submit()
- [x] Add validation for EN_INSCRIPCION state
- [x] Add consent validation

## 3. API
- [x] Create serializers
- [x] Create viewsets with CRUD
- [x] Add save_draft and submit_fui actions
- [x] Configure URLs

## 4. Integration
- [x] Add to INSTALLED_APPS
- [x] Wire to URL config

## 5. Testing
- [x] All 94 tests passing

## Implementation Notes
- Solicitud: radicado, JSON fields, state machine
- Anexo: file upload with SHA-256
- Wizard: 5-step process
- Radicado: FODEJAS-YYYY-NNNNN format
- Integration with CHG-201 (EN_INSCRIPCION check)
- Integration with CHG-105 (consent)

## Dependencies
- CHG-201 (convocatory state)
- CHG-105 (consentimiento)
- CHG-102 (audit)
