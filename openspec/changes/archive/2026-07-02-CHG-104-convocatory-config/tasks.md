# Tasks — CHG-104-convocatory-config

## Review Workload Forecast
- Estimated lines: 180
- Risk assessment: Below 400-line threshold (low risk for single PR)

## 1. Foundation
- [x] Create `ConfiguracionConvocatoria` model in `apps/convocatories/models.py` with JSONField for rules
- [x] Generate and apply initial migration (`python manage.py makemigrations convocatories`)

## 2. Core Implementation
- [x] Implement admin interface in `apps/convocatories/admin.py` for configuration management
- [x] Build domain validators in `apps/convocatories/domain/validators.py`
- [x] Build selectors in `apps/convocatories/selectors.py`
- [x] Build services in `apps/convocatories/services/receta_service.py`

## 3. Testing
- [x] Unit tests for model validation (`apps/convocatories/tests/test_models.py`)
- [x] All 12 tests passing

## 4. Cleanup
- [x] Run `ruff` on modified files (minor style issues remaining in tests)

## Implementation Order
1. Foundation tasks (models/migrations) ✅
2. Core Implementation (admin/domain/services/selectors) ✅
3. Testing ✅
4. Cleanup ✅

## Notes
- forms.py not created (using Django admin built-in validation via full_clean)
- views.py not modified (detail view integration deferred to CAP-002)
- docs/convocatories-configuration.md not created (deferred to follow-up)
