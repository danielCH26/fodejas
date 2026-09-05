# Spec — CHG-112: Asignación de Roles a Usuarios

## Objetivo

Permitir a R-ADMIN asignar roles a usuarios, donde el usuario adquiere los permisos del rol asignado utilizando el sistema nativo de Django.

## Requisito: Integración con Sistema Nativo de Django

**IMPORTANTE**: NO se crearán métodos aislados de verificación de permisos. Se utilizará el sistema nativo de Django:

- `user.has_perm(perm_code)` — verificación de permiso
- `user.has_perms([perm_codes])` — verificación múltiple
- `user.has_module_perms(app_label)` — permisos en módulo

### Cómo funciona la integración

1. **Permission → Django Permission**: Cada `Permission` se sincroniza con `auth.Permission`
2. **Role → Django Group**: Cada `Role` se sincroniza con `auth.Group`
3. **RolePermission → Django Group.permissions**: Los permisos del rol se asignan al grupo
4. **UserRole → Django User.groups**: El usuario se agrega al grupo

Al asignar un rol a un usuario:
```python
user.groups.add(role.group)  # Esto hace que user.has_perm() funcione
```

## Requisitos

### REQ-001: Asignar Rol a Usuario

- **Descripción**: R-ADMIN puede asignar uno o más roles a un usuario
- **Entrada**: usuario_id, lista de role_ids, convocation_scope_id (opcional)
- **Salida**: UserRole creado, usuario agregado al grupo Django
- **Validaciones**:
  - Usuario debe existir y estar activo
  - Rol debe existir
  - No puede tener el mismo rol dos veces (mismo scope)
  - Solo R-ADMIN puede asignar

### REQ-002: Revocar Rol de Usuario

- **Descripción**: R-ADMIN puede remover un rol de un usuario
- **Entrada**: user_role_id
- **Salida**: UserRole eliminado, usuario removido del grupo Django
- **Validaciones**:
  - UserRole debe existir
  - Solo R-ADMIN puede revocar
  - Registrar en auditoría

### REQ-003: Listado de Usuarios con Roles

- **Descripción**: Mostrar todos los usuarios con sus roles actuales
- **Filtros**: por rol, por estado (activo/inactivo)
- **Paginación**: 20 usuarios por página

### REQ-004: Detalle de Usuario con Roles y Permisos

- **Descripción**: Ver detalle de usuario con:
  - Datos personales
  - Roles asignados actualmente
  - Permisos efectivos (calculados desde roles)
  - Historial de cambios de roles
- **Permisos efectivos**: Usar `user.get_all_permissions()` de Django

### REQ-005: Scope de Convocatoria

- **Descripción**: Un rol puede tener alcance específico a una convocatoria
- **Campo**: `convocation_scope_id` en UserRole
- **Uso**: Verificar permisos solo dentro del contexto de una convocatoria específica

### REQ-006: Historial de Cambios de Roles

- **Descripción**: Registrar cada cambio de rol con:
  - Usuario afectado
  - Rol asignado/revocado
  - Usuario que realizó el cambio
  - Timestamp
  - Valores anterior y nuevo
- **Auditoría**: Usar el sistema de auditoría existente (CAP-022)

### REQ-007: Permisos Heredados del Rol

- **Descripción**: El usuario adquiere permisos automáticamente al tener un rol
- **Mecanismo**: Integración con Django Groups
  - Al crear Role → crear auth.Group
  - Al crear Permission → crear auth.Permission
  - Al asignar RolePermission → agregar permiso al Group
  - Al crear UserRole → agregar usuario al Group
- **Verificación**: `user.has_perm('app_label.action')` funciona automáticamente

## Escenarios

### ESC-001: Asignar rol exitosamente

1. R-ADMIN entra a gestión de usuarios
2. Selecciona un usuario
3. Selecciona uno o más roles
4. Opcionalmente selecciona scope de convocatoria
5. Confirma asignación
6. Sistema:
   - Crea UserRole
   - Agrega usuario a Django Group
   - Registra en auditoría
7. Usuario теперь tiene los permisos del rol

### ESC-002: Revocar rol exitosamente

1. R-ADMIN entra a detalle de usuario
2. Ve lista de roles asignados
3. Hace clic en "Revocar" en un rol
4. Confirma la acción
5. Sistema:
   - Elimina UserRole
   - Remueve usuario del Django Group
   - Registra en auditoría

### ESC-003: Usuario cambia de rol

1. Usuario tiene Rol A (tiene permisos X, Y)
2. R-ADMIN le revoca Rol A y asigna Rol B
3. Sistema:
   - Remueve usuario de Group A
   - Agrega usuario a Group B
4. Usuario pierde permisos X, Y y adquiere permisos de B

### ESC-004: Verificar permisos heredados

1. Sistema recibe request con usuario autenticado
2. View verifica: `user.has_perm('applications.view_convocatory')`
3. Django verifica si usuario está en Group con ese permiso
4. Retorna True/False

## Fuera del alcance

- Matriz de permisos visual (para futuro change)
- CRUD de permisos (solo se usan los existentes)
- CRUD de roles (ya existe en CHG-107)
