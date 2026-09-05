# Tasks — CHG-107: Gestión de Usuarios, Roles y Permisos

## 1. Configuración de URLs

- [x] Crear archivo `apps/accounts/urls/admin.py` para las nuevas rutas
- [x] Configurar rutas para:
  - `/accounts/admin/users/` - Listado de usuarios
  - `/accounts/admin/users/crear/` - Crear usuario
  - `/accounts/admin/users/<id>/` - Ver/Editar usuario
  - `/accounts/admin/roles/` - Listado de roles
  - `/accounts/admin/roles/crear/` - Crear rol
- [x] Actualizar `config/urls.py` para incluir nuevas rutas

## 2. Vistas de Gestión de Usuarios

- [x] Crear `UserListView` - Listado con filtros y búsqueda
- [x] Crear `UserCreateView` - Formulario de creación
- [x] Crear `UserUpdateView` - Formulario de edición
- [x] Crear `UserDetailView` - Ver detalle y historial
- [x] Crear `UserToggleActiveView` - Activar/Desactivar usuario

## 3. Vistas de Gestión de Roles

- [x] Crear `RoleListView` - Listado de roles
- [x] Crear `RoleCreateView` - Crear nuevo rol
- [x] Crear `RoleUpdateView` - Editar rol
- [x] Crear `RoleDetailView` - Ver rol con usuarios asignados

## 4. Vistas de Asignación de Roles

- [x] Crear `UserRoleAssignView` - Asignar rol a usuario
- [x] Crear `UserRoleRevokeView` - Revocar rol de usuario

## 5. Templates

- [x] Crear template base para vistas de admin (`admin_base.html`)
- [x] Crear template `users/list.html` - Listado de usuarios
- [x] Crear template `users/form.html` - Formulario usuario
- [x] Crear template `users/detail.html` - Detalle de usuario
- [x] Crear template `roles/list.html` - Listado de roles
- [x] Crear template `roles/form.html` - Formulario rol
- [x] Crear template `roles/detail.html` - Detalle de rol

## 6. Formularios

- [x] Crear `UserAdminForm` para validación
- [x] Crear `RoleAdminForm` para validación
- [x] Crear `UserRoleAssignForm` para asignación

## 7. Permisos

- [x] Crear permission class `IsAdminUser` que verifique rol R-ADMIN
- [x] Aplicar permisos a todas las vistas
- [x] Actualizar menú del dashboard para nuevo flujo

## 8. Auditoría

- [x] Crear señal (signal) para registrar cambios en usuarios
- [x] Crear señal para registrar cambios en roles
- [x] Crear señal para registrar asignación/revocación de roles

## 9. Pruebas

- [x] Tests unitarios para vistas de usuarios
- [x] Tests unitarios para vistas de roles
- [x] Tests de permisos
- [x] Tests de integración (crear, editar, asignar rol)

## 10. Verificación

- [x] Verificar que las vistas cargan correctamente
- [x] Verificar que los permisos funcionan
- [x] Verificar que la auditoría registra los cambios
- [x] Verificar diseño consistente con el resto de la app
