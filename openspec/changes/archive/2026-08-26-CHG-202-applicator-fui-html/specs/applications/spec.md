# Spec for CHG-202 — Interfaz HTML para Wizard FUI

## Purpose

Implementar interfaz HTML para el wizard FUI de inscripción (CAP-003), usando UUIDs en todas las URLs para ocultar IDs secuenciales.

## ADDED Requirements

### Requirement: Modelo Application — Campo UUID

El modelo `Application` SHALL incluir campo `uuid` con las siguientes características:

- Tipo: `UUIDField` con `default=uuid.uuid4`
- Única: `unique=True`
- Indexada: `db_index=True`
- Visible: `editable=False`, `blank=False`

#### Scenario: Nueva aplicación genera UUID automático

- GIVEN modelo Application sin uuid
- WHEN se crea una nueva instancia
- THEN uuid se genera automáticamente con UUID4

#### Scenario: Lookup por UUID en URLs

- GIVEN URL `/applications/550e8400-e29b-41d4-a716-446655440000/`
- WHEN vista procesa la solicitud
- THEN `Application.objects.get(uuid=uuid)` retorna la instancia correcta

### Requirement: URLs HTML con UUID

Todas las URLs HTML SHALL usar UUID en vez de ID secuencial:

| URL | Descripción |
|-----|-------------|
| `/applications/` | Lista de postulaciones |
| `/applications/<uuid>/` | Detalle de postulación |
| `/applications/<uuid>/wizard/` | Wizard de inscripción |
| `/applications/<uuid>/wizard/<step>/` | Paso específico del wizard |

El path converter `uuid` SHALL ser validado por Django.

### Requirement: ApplicationListView

`ApplicationListView` SHALL:

- Heredar de `LoginRequiredMixin`, `TemplateView`
- Mostrar solo las postulaciones del usuario autenticado
- Incluir columnas: convocatoria, estado, radicado, fecha radicación
- Link a detail view con UUID

#### Scenario: Usuario ve sus postulaciones

- GIVEN usuario autenticado con 3 aplicaciones
- WHEN visita `/applications/`
- THEN ve las 3 postulaciones con enlaces a `/applications/<uuid>/`

### Requirement: ApplicationDetailView

`ApplicationDetailView` SHALL:

- Heredar de `LoginRequiredMixin`, `DetailView`
- Buscar por `uuid` (no pk)
- Verificar que el usuario sea el propietario
- Mostrar: radicado, estado, datos del formulario, anexos
- Incluir botón para continuar wizard si está en estado `borrador`

#### Scenario: Acceso no autorizado

- GIVEN usuario A intenta acceder a `/applications/<uuid-de-B>/`
- WHEN vista procesa
- THEN retorna 404 (no revela existencia del registro)

### Requirement: ApplicationWizardView

`ApplicationWizardView` SHALL:

- Implementar wizard de 5 pasos usando HTMX
- Usar `UUIDConverter` para el path
- Persistir cada paso via `save_draft(step, data)`
- Mostrar progress indicator (steps 1-5)

Pasos del wizard:
1. Datos personales
2. Información académica / Excelencia
3. Información socioeconómica
4. Anexos (upload)
5. Declaración y consentimiento

#### Scenario: Guardar draft parcialmente

- GIVEN usuario en paso 2 del wizard
- WHEN ingresa datos y hace click en "Guardar"
- THEN HTMX envía POST a `/applications/<uuid>/wizard/2/`
- AND datos se guardan en `Application.datos_personales` (JSON)
- AND usuario permanece en paso 2

#### Scenario: Upload de anexos

- GIVEN usuario en paso 4
- WHEN sube archivo via drag-drop
- THEN archivo se guarda en S3
- AND se crea registro `Anexo` asociado
- AND progreso se muestra en UI

### Requirement: Submit — Transición a radicada

El botón "Radicar" SHALL:

- Verificar que todos los pasos estén completos
- Generar radicado único via `generar_radicado()`
- Cambiar estado de `borrador` a `radicada`
- Generar PDF del formulario
- Redireccionar a detail view con mensaje de éxito

#### Scenario: Submit exitoso

- GIVEN wizard con todos los pasos completos
- WHEN usuario hace click en "Radicar"
- THEN estado cambia a `radicada`
- AND radicado se muestra como `FODEJAS-2026-00001`
- AND PDF se genera y es descargable

### Requirement: Templates HTML

| Template | Descripción |
|----------|-------------|
| `applications/list.html` | Lista de postulaciones |
| `applications/detail.html` | Detalle con radicado |
| `applications/wizard.html` | Wizard base con progress |
| `applications/partials/wizard_step_1.html` | Paso 1 - Datos personales |
| `applications/partials/wizard_step_2.html` | Paso 2 - Académica |
| `applications/partials/wizard_step_3.html` | Paso 3 - Socioeconómica |
| `applications/partials/wizard_step_4.html` | Paso 4 - Anexos |
| `applications/partials/wizard_step_5.html` | Paso 5 - Declaración |

Todos los templates SHALL usar `{% url %}` con namespaces correctos.

### Requirement: Seguridad — UUID como obfuscation

- GIVEN usuario malicioso intenta acceso por fuerza bruta a UUIDs
- WHEN intenta acceder a `/applications/<uuid-aleatorio>/`
- THEN sistema retorna 404 (no revela existencia)
- AND no hay diferencia entre "no existe" y "no tiene acceso"

## MODIFIED Files

- `apps/applications/models.py` — agregar campo `uuid`
- `apps/applications/views.py` — agregar vistas HTML
- `apps/applications/urls.py` — agregar URLs con UUID
- `templates/applications/` — crear templates

## Acceptance Criteria

- [ ] Campo `uuid` existe en modelo Application
- [ ] Todas las URLs HTML usan `<uuid:pk>`
- [ ] Lista de postulaciones muestra正确的 enlaces
- [ ] Detail view muestra radicado y estado
- [ ] Wizard permite guardar drafts en cada paso
- [ ] Upload de anexos funciona con progress
- [ ] Submit genera radicado y cambia estado
- [ ] Acceso no autorizado retorna 404
- [ ] Tests unitarios pasan
- [ ] Tests de integración del wizard flow pasan
