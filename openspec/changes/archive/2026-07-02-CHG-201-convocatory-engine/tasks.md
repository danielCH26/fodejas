# Tasks — CHG-201-convocatory-engine

## Review Workload Forecast
- Estimated lines: 350
- Risk assessment: Below 400-line threshold (low risk for single PR)

## 1. FSM Implementation
- [x] Create domain/transitions.py with TRANSICIONES_PERMITIDAS dict
- [x] Implement transicionar() function with validation
- [x] Add Estado class with constants

## 2. Service Layer
- [x] Create services/convocatoria_service.py
- [x] Implement publicar() with config validation
- [x] Implement cerrar()
- [x] Implement cancelar()
- [x] Add audit logging
- [x] Add notifications (CHG-106 integration)

## 3. API Endpoints
- [x] Create api/serializers.py with TransitionSerializer
- [x] Create api/views.py with ConvocatoryViewSet
- [x] Add /transicionar/, /publicar/, /cerrar/, /cancelar/ endpoints
- [x] Configure urls.py

## 4. Admin Integration
- [x] Update admin.py: set estado as readonly
- [x] Add transition actions (publicar, cerrar, cancelar)
- [x] Add bulk actions

## 5. Testing
- [x] All 94 tests passing

## Implementation Notes
- FSM: 8 states (borrador -> publicada -> en_inscripcion -> en_verificacion -> en_calificacion -> definitiva -> cerrada)
- Cancelada is terminal from any active state
- Services enforce state transitions (no direct writes)
- Audit logging for all transitions
- Notifications sent on publish/close (CHG-106)

## Dependencies
- CHG-104 (ConfiguracionConvocatoria)
- CHG-106 (notifications)
- CHG-102 (audit)
