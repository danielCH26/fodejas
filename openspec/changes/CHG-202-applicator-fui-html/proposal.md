# CHG-202 — Interfaz HTML para Wizard FUI (Inscripción)

## Contexto

La spec `applicator-fui` (CAP-003) define el wizard FUI digital con 5 pasos, pero actualmente solo existe la API REST (`/api/applications/solicitudes/`). Los usuarios acceden a JSON en vez de una interfaz HTML usable.

## Capacidades afectadas

- **CAP-003** — Wizard FUI digital + carga de anexos + radicado
- **CAP-002** — Ciclo de estados de convocatoria (dependencia: `en_inscripcion`)

## Reglas de negocio afectadas

- `project.md` §10.2 — Pasos 2–5 del FUI digital
- `project.md` §12.3 — Convocatoria de ejemplo "Reconocimiento a la Excelencia"

## Cambios propuestos

1. **Vistas HTML** en `apps/applications/views.py`:
   - `ApplicationListView` — lista de postulaciones del usuario
   - `ApplicationWizardView` — wizard de 5 pasos con HTMX
   - `ApplicationDetailView` — detalle de postulación con radicado

2. **URLs HTML** en `apps/applications/urls.py`:
   - `/applications/` — lista de postulaciones
   - `/applications/<uuid:pk>/` — detalle
   - `/applications/<uuid:pk>/wizard/` — wizard de inscripción
   - `/applications/<uuid:pk>/wizard/<step>/` — paso específico

3. **Modelo Application** — agregar campo `uuid` único (UUID4) si no existe

3. **Templates** en `templates/applications/`:
   - `list.html` —mis postulaciones
   - `wizard.html` — wizard multipaso con progress indicator
   - `detail.html` — detalle con PDF descargable

4. **HTMX partials** para cada paso del wizard

## Criterios de aceptación

- [ ] Usuario puede ver lista de sus postulaciones en `/applications/`
- [ ] Usuario puede iniciar wizard de inscripción en `/applications/<uuid:pk>/wizard/`
- [ ] Wizard muestra 5 pasos con progress indicator
- [ ] Cada paso guarda draft vía HTMX sin recargar página
- [ ] Upload de anexos funciona con drag-drop y progress
- [ ] Submit genera radicado y muestra PDF
- [ ] Vista detail muestra radicado único y estado
- [ ] **Todas las URLs usan UUID** — ningún ID secuencial visible en URLs (POST/GET)
- [ ] **IDs internos solo en API** — la API REST puede seguir usando IDs, pero HTML usa UUID

## Pruebas

- Tests unitarios para cada vista HTML
- Tests de integración para wizard flow
- Verificar que todas las URLs generen HTML (no JSON)

## Riesgos

- Dependencia de HTMX existente en el proyecto
- Upload de archivos grandes requiere configuración S3

## Outside Scope

- API REST (ya existe, puede seguir usando IDs)
- Scoring (CHG-204)
- Reclamaciones/Apelaciones (CHG-205/206)

## Notas de implementación

- Agregar campo `uuid` a modelo `Application` (UUID4, único, indexed)
- Usar `get_object_or_404(Application, uuid=uuid)` en vistas
- El campo `uuid` será visible solo en URLs HTML; internos usan PK
