# Tasks — CHG-401 Seguimiento Académico

## 1. Setup

- [x] 1.1 Create models in apps/academic_tracking/models.py (AcademicRecord, GradeEntry)
      (pre-existing, CHG-802 era: + `AcademicAlert` con tipos BAJO_RENDIMIENTO/
      PROBACION/SUSPENSION/GRADUACION — tercer modelo no listado en la tarea)
- [x] 1.2 Create migrations for academic_tracking app (pre-existing, CHG-802)
- [x] 1.3 Add admin interfaces in apps/academic_tracking/admin.py
      (pre-existing: los 3 modelos registrados con list_display)

## 2. Core Implementation

- [x] 2.1 Implement AcademicTrackingService in apps/academic_tracking/services.py
      (pre-existing, CHG-802 era: create/add_grade/recalculate/alerts/resolve/
      mark_graduated)
- [x] 2.2 Add grade calculation utilities
      (pre-existing: `calculate_semester_average`/`calculate_cumulative_average`
      ponderadas por créditos; verificadas a mano en tests)
- [x] 2.3 Add alert generation logic
      (pre-existing + bug corregido: `CONSECUTIVE_LOW_SEMESTRES_TRIGGER` estaba
      SIN DEFINIR — la suspensión automática del Art. 16 crasheaba con NameError
      bajo un `# noqa: F821` mentiroso; definida = 2 según design.md)
- [x] 2.4 Add cumulative average calculation
      (pre-existing; umbrales 3.5/3.0 según design)

## 3. API/Views

- [x] 3.1 Create API views in apps/academic_tracking/views.py
      (ViewSets pre-existentes completados: `serializers.py` nuevo
      (AcademicRecord con grades/alerts anidados, AcademicAlert),
      `IsAdminUser` en ambos ViewSets)
- [x] 3.2 Add URL routes in apps/academic_tracking/urls.py
      (router pre-existente; faltaba incluirlo en `config/urls.py` —
      corregido: `/api/academic-tracking/`)

## 4. Testing

- [x] 4.1 Write unit tests for AcademicTrackingService
      (`test_services.py::TestAcademicTrackingService`: suspensión automática
      por 2 semestres bajos consecutivos, guard de semestre alto, alertas,
      graduación, idempotencia de add_grade)
- [x] 4.2 Write unit tests for grade calculations
      (`test_services.py::TestAverages`: ponderación por créditos verificada
      a mano, umbrales 3.5/3.0)
- [x] 4.3 Write integration tests for academic workflow
      (`test_api.py`: gating por rol, retrieve con grades/alerts anidados,
      add_grade y resolve vía API; `TestAuditTrail`: CREATE/UPDATE en la
      cadena CAP-022)

## Batch notes (2026-10-10)

- La lógica de dominio existía desde la era CHG-802; gaps reales: serializers
  TODO, router sin incluir en config/urls.py, y el NameError latente del
  trigger de suspensión (oculto bajo `# noqa: F821` con un test legacy vacío
  que lo dejaba pasar).
- **Auditoría añadida en este batch**: eventos CAP-022 en creación de
  expediente, transiciones de estado (solo si cambia) y graduación
  (`module="academic_tracking"`, sin try/except).
- Reemplazado `tests.py` legacy (un test con `pass`) por paquete `tests/`.
- **Matriz de roles fina (CAP-011) completada**: ViewSets de
  academic_record y academic_alert ahora usan `_AcademicRolePermission`
  con roles `['R-COORD', 'R-ADMIN']`. Ghost code `R-COORDINADOR`
  reemplazado por `R-COORD`.
- Pendiente: umbrales configurables por convocatoria (design lo sugiere,
  hoy constantes de módulo).
