# Tasks — CHG-202 Interfaz HTML para Wizard FUI

## 1. Agregar campo UUID al modelo Application

- [x] 1.1 Agregar campo `uuid` a `apps/applications/models.py`
- [x] 1.2 Crear migración Django
- [x] 1.3 Ejecutar migración
- [x] 1.4 Agregar `uuid` a serializadores existentes (si aplica)

## 2. Crear vistas HTML

- [x] 2.1 Crear `ApplicationListView` en `apps/applications/views.py`
- [x] 2.2 Crear `ApplicationDetailView` (buscar por uuid)
- [x] 2.3 Crear `ApplicationWizardView` con los 5 pasos
- [x] 2.4 Agregar permisos `login_required` a todas las vistas

## 3. Configurar URLs con UUID

- [x] 3.1 Configurar `app_name = "applications"` en `urls.py`
- [x] 3.2 Agregar rutas con `<uuid:pk>`
- [x] 3.3 Incluir URLs en `config/urls.py`

## 4. Crear templates

- [x] 4.1 Crear directorio `templates/applications/`
- [x] 4.2 Crear `list.html` — lista de postulaciones
- [x] 4.3 Crear `detail.html` — detalle con radicado
- [x] 4.4 Crear `wizard.html` — base del wizard
- [x] 4.5 Crear partials para cada paso (1-5)

## 5. Implementar funcionalidad wizard

- [x] 5.1 Conectar wizard con `wizard_service.save_draft()`
- [x] 5.2 Implementar upload de anexos con progress
- [x] 5.3 Implementar submit con generación de radicado
- [x] 5.4 Agregar validaciones de cada paso

## Estado

- ✅ Todas las tareas completadas
- ✅ CHG-202 verificado (QA passed)

## 6. Pruebas

- [x] 6.1 Tests unitarios para vistas
- [x] 6.2 Tests de integración wizard flow
- [x] 6.3 Verificar que URLs usen UUID

## 7. Verificación manual

- [x] 7.1 Acceder a `/applications/` como usuario autenticado
- [x] 7.2 Crear postulación y verificar UUID en URL
- [x] 7.3 Completar wizard hasta submit
- [x] 7.4 Verificar radicado generado

## Notas de QA (2026-07-06)

- Login funciona con CSRF
- Lista de postulaciones carga correctamente
- Wizard FUI carga con UUID
- Todos los 5 pasos del wizard implementados
- Upload de anexos configurado
