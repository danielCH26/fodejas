# Tasks — CHG-108-audit-ui (Interfaz HTML de Auditoría)

## 1. Permisos de Auditoría

- [ ] Crear `IsAuditViewer` en `apps/accounts/permissions.py` — permite R-ADMIN y R-CONTROL
- [ ] Crear `IsAuditAdmin` en `apps/accounts/permissions.py` — permite solo R-ADMIN

## 2. Model Selectors

- [ ] Crear `apps/audit/selectors.py` con funciones:
  - `get_audit_events(filters)` — listado con filtros
  - `get_audit_event_by_id(id)` — detalle
  - `verify_audit_chain()` — verificación de hash chain

## 3. Vistas HTML

- [ ] Crear `AuditDashboardView` — `/accounts/audit/`
- [ ] Crear `AuditEventDetailView` — `/accounts/audit/<uuid:id>/`
- [ ] Crear `AuditChainVerifyView` — `/accounts/audit/verify/`
- [ ] Configurar URLs en `apps/accounts/urls.py` (namespace `audit`)

## 4. Templates

- [ ] `audit/base.html` — Layout base con sidebar de navegación
- [ ] `audit/index.html` — Listado con filtros (forma, tabla paginada)
- [ ] `audit/detail.html` — Detalle de evento con diff de cambios
- [ ] `audit/verify.html` — Resultado de verificación de cadena

## 5. Navegación

- [ ] Actualizar `apps/accounts/accounts_views.py` — cambiar URL de auditoría a `/accounts/audit/`

## 6. Pruebas

- [ ] Test: `R-ADMIN` tiene acceso a `/accounts/audit/`
- [ ] Test: `R-CONTROL` tiene acceso a `/accounts/audit/`
- [ ] Test: usuario sin rol permitido recibe 403
- [ ] Test: filtros funcionan correctamente
- [ ] Test: verificación de cadena devuelve resultado válido

## 7. Documentación

- [ ] Actualizar `AGENTS.md` con el mapeo de capacidad si es necesario
