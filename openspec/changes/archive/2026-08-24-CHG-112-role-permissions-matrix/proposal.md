# CHG-112: Asignación de Roles a Usuarios

## Contexto

El sistema tiene un modelo de roles y permisos, pero falta la funcionalidad para asignar roles a usuarios de manera completa. El usuario debe adquirir los permisos del rol asignado, similar a cómo Django maneja permisos.

## Capacidades afectadas

- **CAP-001** — Autenticación y Gestión de Usuarios/Roles

## Reglas de negocio afectadas

- project.md §7 — Roles del sistema (R-ADMIN, R-COORD, R-CT, etc.)

## Estado actual

El sistema tiene:
- `Role`: código, nombre, tipo, descripción
- `Permission`: app_label, action, convocation_scope_id, stage
- `RolePermission`: relación rol ↔ permiso (M2M)
- `UserRole`: relación usuario ↔ rol (M2M)

**Falta**: Interfaz completa para asignar roles a usuarios.

## Cambios propuestos

### 1. Asignar Rol a Usuario

Vistas para:
- Listar usuarios con sus roles actuales
- Asignar uno o más roles a un usuario
- Asignar rol con alcance de convocatoria específico (opcional)
- Revocar roles de un usuario
- Ver historial de cambios de roles por usuario

### 2. Permisos Heredados del Rol

El usuario adquiere automáticamente los permisos de los roles asignados:
- El sistema debe verificar permisos basado en los roles del usuario
- Utilizar `RolePermission` para determinar qué permisos tiene un rol
- Los permisos se calculan dinámicamente desde los roles asignados

### 3. Mejora de Detalle de Usuario

En la vista de detalle de usuario:
- Mostrar roles asignados actualmente
- Mostrar permisos efectivos (calculados desde los roles)
- Historial de cambios de roles

## Criterios de aceptación

- [ ] Se puede asignar uno o más roles a un usuario
- [ ] Se puede asignar rol con scope de convocatoria específico
- [ ] Se puede revocar roles de un usuario
- [ ] Los permisos del usuario se calculan desde sus roles asignados
- [ ] Se muestra historial de cambios de roles
- [ ] Toda acción queda registrada en auditoría
- [ ] Solo R-ADMIN puede acceder

## Pruebas

- Verificar que usuario con rol adquiere los permisos del rol
- Verificar asignación y revocación de roles
- Verificar auditoría de cambios
