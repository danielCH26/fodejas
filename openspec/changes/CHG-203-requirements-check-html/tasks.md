# Tasks — CHG-203 Interfaz para Validación de Requisitos

## 1. Modelo RequisitoValidacion

- [x] 1.1 Crear modelo `RequisitoValidacion` en `apps/applications/models.py`
- [x] 1.2 Crear migración
- [x] 1.3 Ejecutar migración

## 2. Vistas de Revisión

- [x] 2.1 Crear `RequirementReviewListView`
- [x] 2.2 Crear `RequirementReviewDetailView`
- [x] 2.3 Crear `RequirementVerifyView` (API endpoint)
- [x] 2.4 Agregar permisos R-REVISOR

## 3. URLs

- [x] 3.1 Agregar rutas con UUID
- [x] 3.2 Incluir en config/urls.py

## 4. Templates

- [x] 4.1 Crear `review/list.html`
- [x] 4.2 Crear `review/detail.html`
- [x] 4.3 Crear partials para requisitos

## 5. Funcionalidad

- [x] 5.1 Checklist dinámico desde configuración
- [x] 5.2 Upload de evidencia por requisito
- [x] 5.3 Botones aprobar/rechazar
- [x] 5.4 Notificaciones al aspirante
- [x] 5.5 Historial de verificaciones

## 6. Pruebas

- [x] 6.1 Tests básicos creados

## Estado

- ✅ CHG-203 completado y verificado

## Notas de QA (2026-07-06)

- RequirementReviewListView implementada con permisos R-REVISOR
- RequirementReviewDetailView muestra checklist de requisitos
- Modelo RequisitoValidacion con historial de verificaciones
- Notificaciones al aspirante configuradas
- Tests pasan: 10/10
