# Tasks — CHG-304 Causales de Terminación y Sanciones

## 1. Setup

- [x] 1.1 Create models in apps/condonation/models.py (TerminationRequest, Sanction)
      (pre-existing, CHG-802 era: `TerminationRequest.Cause` cubre Art. 14/15;
      `Sanction.Justification` cubre Art. 17)
- [x] 1.2 Create migrations for condonation app
      (pre-existing: 0001 inicial + 0002_add_fecha_limite_and_vencido, CHG-802)
- [x] 1.3 Add admin interfaces in apps/condonation/admin.py
      (pre-existing y completo: list_display/filters/search/fieldsets para ambos modelos)

## 2. Core Implementation

- [x] 2.1 Implement TerminationService in apps/condonation/services.py
      (pre-existing, CHG-802 era: create/approve/reject/handle_death_termination)
- [x] 2.2 Implement SanctionService in apps/condonation/services.py
      (pre-existing, CHG-802 era: create/approve/reject/justification/expiry/condone/payment)
- [x] 2.3 Add IPC calculation utilities
      (pre-existing: `calculate_ipc_adjustment`; fórmula verificada con valor
      calculado a mano en `test_services.py::TestCalculateIpcAdjustment`)
- [x] 2.4 Add justification validation
      (pre-existing: validación contra `Sanction.Justification` choices + ventana
      de 30 días con `fecha_limite`, Decreto 0372/2025 Art. 17)

## 3. API/Views

- [x] 3.1 Create API views in apps/condonation/views.py
      (ViewSets pre-existentes completados: `serializers.py` nuevo con
      TerminationRequestSerializer/SanctionSerializer; permisos `IsAdminUser`
      en los ViewSets y `IsAuthenticated` en la acción
      `submit_justification`; pendiente matriz de roles fina para CAP-015/016)
- [x] 3.2 Add URL routes in apps/condonation/urls.py
      (router pre-existente; faltaba incluirlo en `config/urls.py` —
      la API era inalcanzable. Corregido: `/api/condonation/`)

## 4. Testing

- [x] 4.1 Write unit tests for TerminationService
      (`test_services.py::TestTerminationService`: causales, transiciones,
      muerte con condonación, guardas de doble transición)
- [x] 4.2 Write unit tests for SanctionService
      (`test_services.py::TestSanctionService`: IPC verificado a mano,
      ventana 30 días, expiración idempotente, condonación, pago)
- [x] 4.3 Write integration tests for termination workflow
      (`test_api.py::TestTerminationAPI`: gating por rol, creación,
      aprobación vía API)
- [x] 4.4 Write integration tests for sanction workflow
      (`test_services.py::TestAuditTrail` + `test_api.py::TestSanctionAPI`:
      flujo sanción→justificación→condonación/pago con eventos de auditoría)

## Batch notes (2026-10-10)

- Toda la lógica de dominio existía desde la era CHG-802; el gap real era
  exposición (serializers TODO, router sin incluir) y cobertura de tests.
- **Auditoría añadida en este batch**: los servicios no emitían eventos
  CAP-022; ahora cada cambio de estado escribe en la cadena
  (`module="condonation"`, sin try/except — la falla de auditoría revierte
  la operación).
- **Matriz de roles fina (CAP-015/016) completada**: ViewSets de
  termination y sanction ahora usan `_RolePermission` con roles
  `['R-JUNTA', 'R-ADMIN', 'R-COORD']`. La acción `submit_justification`
  tiene verificación de ownership (beneficiary del proceso o staff-de-flujo).
  Ghost codes `R-COORDINADOR`/`R-TESORERO` reemplazados por `R-COORD`/`R-TESOR`.
- Pendiente: confirmar con Negociación jurídica el cálculo definitivo del IPC
  (Art. 17) — hoy es tasa anual simple configurable.
