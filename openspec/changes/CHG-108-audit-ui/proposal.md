# CHG-108-audit-ui — Interfaz HTML de Auditoría (CAP-022)

## Contexto

El módulo de auditoría (`CHG-102`, CAP-022) fue implementado con:
- Modelo `AuditEvent` con hash chain criptográfico
- Señales automático (`post_save`, `post_delete`)
- API REST (`/api/audit/events/`, `/api/audit/verify/`)

**Sin embargo**, no existe interfaz HTML para que los administradores (`R-ADMIN`, `R-CONTROL`) puedan visualizar los eventos de auditoría desde la plataforma web. Actualmente solo доступ через API.

El dashboard ya tiene el enlace a `/api/audit/` pero no hay una vista HTML对应的.

## Capacidades afectadas

- **CAP-022** — Bitácora de Auditoría (existente, extender)
- **CAP-017** — RBAC: extender permisos de acceso a auditoría

## Reglas de negocio afectadas

- `project.md §13.3` — Bitácora de Auditoría (accesible visualmente)
- `project.md §7.3` — Roles con acceso a auditoría (`R-ADMIN`, `R-CONTROL`)

## Cambios propuestos

### 1. Vistas HTML de Auditoría

Crear vistas basadas en clase Django para mostrar eventos de auditoría:

| Vista | URL | Descripción |
|-------|-----|-------------|
| `AuditDashboardView` | `/accounts/audit/` | Panel principal con filtros y listado paginado |
| `AuditEventDetailView` | `/accounts/audit/<uuid:id>/` | Detalle de un evento con cambios antes/después |
| `AuditChainVerifyView` | `/accounts/audit/verify/` | Verificar integridad de la cadena de hash |

### 2. Permisos

- `IsAuditViewer`: acceso a ver auditoría (`R-ADMIN`, `R-CONTROL`)
- `IsAuditAdmin`: acceso a verificar cadena (`R-ADMIN` solo)

### 3. Templates

- `audit/audit_base.html` — Base layout con sidebar
- `audit/index.html` — Listado con filtros (actor, entidad, acción, fecha)
- `audit/detail.html` — Detalle de evento individual
- `audit/verify.html` — Resultado de verificación de cadena

### 4. Navegación

Actualizar el dashboard para que los enlaces de auditoría apunten a `/accounts/audit/` en lugar de `/api/audit/`.

## Criterios de aceptación

- [ ] El usuario con rol `R-ADMIN` puede ver el listado de eventos de auditoría
- [ ] El usuario con rol `R-CONTROL` puede ver el listado de eventos de auditoría
- [ ] Los filtros por actor, entidad, acción y fecha funcionan correctamente
- [ ] El detalle de un evento muestra: actor, acción, entidad, timestamp, IP, cambios (before/after)
- [ ] La verificación de cadena hash muestra resultado visual (válido/inválido)
- [ ] usuarios sin permiso ven error 403
- [ ] usuarios no autenticados son redirigidos a login

## Pruebas

- Tests de permisos: `R-ADMIN` y `R-CONTROL` tienen acceso; otros roles no
- Tests de filtros: verificar querysets filtrados
- Tests de templates: verificar renderizado con datos reales

## Riesgos y Fuera del alcance

- **Riesgo**: rendimiento con grandes volúmenes de eventos → implementar paginación + índices
- **Fuera de alcance**: exportación PDF/Excel (futuro CAP-028), alertas automáticas
