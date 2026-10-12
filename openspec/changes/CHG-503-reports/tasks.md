# Tasks — CHG-503: Reportes de Gestión

## 1. App
- [ ] 1.1 Recrear `apps/reporting/` (apps.py, INSTALLED_APPS)
- [ ] 1.2 `ReportingService` con agregaciones de §14.1

## 2. API
- [ ] 2.1 Endpoint `/api/reporting/gestion/` (read-only, periodo)
- [ ] 2.2 Gating R-COORD/R-JUNTA/R-ADMIN + sin PII

## 3. Testing
- [ ] 3.1 Unitarias de KPIs con datos sintéticos
- [ ] 3.2 API: gating, periodo, sin PII
- [ ] 3.3 Suite completa verde en sqlite y PostgreSQL
