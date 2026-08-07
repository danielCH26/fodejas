# CHG-203 — Interfaz HTML para Validación de Requisitos

## Contexto

La spec de requirements-check (CAP-004) define la validación de requisitos mínimos por la Coordinación Técnica. Actualmente no existe interfaz HTML — los revisores acceden a la API REST. Se necesita una UI para verificar requisitos, adjuntar evidencia y aprobar/rechazar solicitudes.

## Capacidades afectadas

- **CAP-004** — Validación de requisitos mínimos + subsanaciones
- **CAP-002** — Ciclo de estados de convocatoria

## Reglas de negocio afectadas

- `project.md` §10.2 — Verificación de los 7 requisitos mínimos
- Verificación manual contra SNIES/SISBÉN/OCCRE registrada como evidencia
- Subsanaciones允许 correcciones antes de scoring

## Cambios propuestos

1. **Vistas HTML** en `apps/applications/views.py`:
   - `RequirementReviewListView` — lista de solicitudes en verificación
   - `RequirementReviewDetailView` — verificación de requisitos por solicitud
   - `RequirementVerifyView` — acción de aprobar/rechazar con observaciones

2. **URLs HTML** con UUID:
   - `/applications/<uuid>/revisión/` — detalle de verificación
   - `/applications/<uuid>/revisión/<requisito>/` — verificar requisito específico

3. **Templates**:
   - `applications/review/list.html` — lista de solicitudes a verificar
   - `applications/review/detail.html` — checklist de requisitos
   - `applications/review/partials/requisito_item.html` — cada requisito

4. **Modelo de verificación**:
   - `RequisitoValidacion(solicitud, requisito, estado, evidencia, observaciones, validado_por, fecha)`

## Criterios de aceptación

- [ ] Revisores ven lista de solicitudes en `en_verificacion`
- [ ] Cada requisito muestra checkbox + campo de evidencia + observaciones
- [ ] Upload de evidencia (PDF/images) por requisito
- [ ] Botones Aprobar/Rechazar con validaciones
- [ ] Historial de verificaciones visible
- [ ] Notificación al aspirante de resultado
- [ ] Todas las URLs usan UUID

## Pruebas

- Tests de flujo de verificación
- Verificar permisos por rol (solo R-REVISOR)

## Outside Scope

- Scoring (CHG-204)
- Reclamaciones (CHG-205)
- API REST de requisitos (ya existe)

## Notas

- Usar UUID en URLs (igual que CHG-202)
- Permisos: solo usuarios con rol R-REVISOR pueden acceder
- Integración con sistema de notificaciones (CHG-106)
