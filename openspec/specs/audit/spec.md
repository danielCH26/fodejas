# Audit UI Specification — CHG-108

## ADDED

### Requirements

#### AUDIT-UI-001: Dashboard de Auditoría
El sistema SHALL mostrar un dashboard HTML en `/accounts/audit/` que presente un listado paginado de eventos de auditoría con filtros.

**Criterios de aceptación:**
- Filtro por actor (dropdown de usuarios)
- Filtro por acción (CREATE, UPDATE, DELETE, LOGIN, LOGOUT)
- Filtro por entidad (Convocatory, User, Role, etc.)
- Filtro por rango de fechas
- Paginación de 50 eventos por página

#### AUDIT-UI-002: Detalle de Evento
El sistema SHALL mostrar el detalle de un evento de auditoría en `/accounts/audit/<uuid:id>/`.

**Criterios de aceptación:**
- Mostrar: timestamp, actor, acción, entidad, entity_id
- Mostrar: dirección IP, user agent
- Mostrar: cambios (before/after) si aplica
- Mostrar: hash actual y hash anterior

#### AUDIT-UI-003: Verificación de Cadena
El sistema SHALL permitir verificar la integridad de la cadena de hash en `/accounts/audit/verify/`.

**Criterios de aceptación:**
- Ejecutar `verify_chain()` del servicio
- Mostrar resultado: is_valid, last_valid_hash, break_point
- Indicador visual: verde (válido) / rojo (inválido)

#### AUDIT-UI-004: Control de Acceso
El sistema SHALL restringir el acceso a las vistas de auditoría.

**Criterios de aceptación:**
- `R-ADMIN`: acceso completo (ver + verificar cadena)
- `R-CONTROL`: acceso a ver eventos (no verificar cadena)
- Otros roles: HTTP 403 Forbidden
- Usuarios no autenticados: redirect a login

### Scenarios

#### Scenario: Administrador visualiza eventos de auditoría
**Given** el usuario tiene rol `R-ADMIN`  
**And** está autenticado  
**When** navega a `/accounts/audit/`  
**Then** ve el listado de eventos paginado  
**And** puede aplicar filtros por acción, entidad, actor y fecha

#### Scenario: Usuario no autorizado intenta acceder
**Given** el usuario tiene rol `R-ASPIRANTE`  
**And** está autenticado  
**When** navega a `/accounts/audit/`  
**Then** recibe HTTP 403 Forbidden

#### Scenario: Verificación de cadena exitosa
**Given** el usuario tiene rol `R-ADMIN`  
**When** navega a `/accounts/audit/verify/`  
**And** la cadena no ha sido alterada  
**Then** ve indicador verde "Cadena de auditoría válida"
