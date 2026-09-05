# Tasks — CHG-108-audit-ui (Interfaz HTML de Auditoría)

## 1. Permisos de Auditoría

- [x] Crear `IsAuditViewer` en `apps/accounts/permissions.py` — permite R-ADMIN y R-CONTROL
- [x] Crear `IsAuditAdmin` en `apps/accounts/permissions.py` — permite solo R-ADMIN

## 2. Model Selectors

- [x] Crear `apps/audit/selectors.py` con funciones:
  - `get_audit_events(filters)` — listado con filtros
  - `get_audit_event_by_id(id)` — detalle
  - `verify_audit_chain()` — verificación de hash chain

## 3. Vistas HTML

- [x] Crear `AuditDashboardView` — `/accounts/audit/`
- [x] Crear `AuditEventDetailView` — `/accounts/audit/<uuid:id>/`
- [x] Crear `AuditChainVerifyView` — `/accounts/audit/verify/`
- [x] Configurar URLs en `apps/accounts/urls.py` (namespace `audit`)

## 4. Templates

- [x] `audit/base.html` — Layout base con sidebar de navegación
- [x] `audit/index.html` — Listado con filtros (forma, tabla paginada)
- [x] `audit/detail.html` — Detalle de evento con diff de cambios
- [x] `audit/verify.html` — Resultado de verificación de cadena

## 5. Navegación

- [x] Actualizar `apps/accounts/accounts_views.py` — cambiar URL de auditoría a `/accounts/audit/`

## 6. Pruebas

- [x] Test: `R-ADMIN` tiene acceso a `/accounts/audit/`
- [x] Test: `R-CONTROL` tiene acceso a `/accounts/audit/`
- [x] Test: usuario sin rol permitido recibe 403
- [x] Test: filtros funcionan correctamente
- [x] Test: verificación de cadena devuelve resultado válido

## 7. Documentación

- [x] Actualizar `AGENTS.md` con el mapeo de capacidad si es necesario
