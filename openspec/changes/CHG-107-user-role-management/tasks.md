# Tasks — CHG-107: Gestión de Usuarios, Roles y Permisos

## 1. Configuración de URLs

- [ ] Crear archivo `apps/accounts/urls/admin.py` para las nuevas rutas
- [ ] Configurar rutas para:
  - `/accounts/admin/users/` - Listado de usuarios
  - `/accounts/admin/users/crear/` - Crear usuario
  - `/accounts/admin/users/<id>/` - Ver/Editar usuario
  - `/accounts/admin/roles/` - Listado de roles
  - `/accounts/admin/roles/crear/` - Crear rol
  - [ ] Actualizar `config/urls.py` para incluir nuevas rutas

## 2. Vistas de Gestión de Usuarios

- [ ] Crear `UserListView` - Listado con filtros y búsqueda
- [ ] Crear `UserCreateView` - Formulario de creación
- [ ] Crear `UserUpdateView` - Formulario de edición
- [ ] Crear `UserDetailView` - Ver detalle y historial
- [ ] Crear `UserToggleActiveView` - Activar/Desactivar usuario

## 3. Vistas de Gestión de Roles

- [ ] Crear `RoleListView` - Listado de roles
- [ ] Crear `RoleCreateView` - Crear nuevo rol
- [ ] Crear `RoleUpdateView` - Editar rol
- [ ] Crear `RoleDetailView` - Ver rol con usuarios asignados

## 4. Vistas de Asignación de Roles

- [ ] Crear `UserRoleAssignView` - Asignar rol a usuario
- [ ] Crear `UserRoleRevokeView` - Revocar rol de usuario

## 5. Templates

- [ ] Crear template base para vistas de admin (`admin_base.html`)
- [ ] Crear template `users/list.html` - Listado de usuarios
- [ ] Crear template `users/form.html` - Formulario usuario
- [ ] Crear template `users/detail.html` - Detalle de usuario
- [ ] Crear template `roles/list.html` - Listado de roles
- [ ] Crear template `roles/form.html` - Formulario rol
- [ ] Crear template `roles/detail.html` - Detalle de rol

## 6. Formularios

- [ ] Crear `UserAdminForm` para validación
- [ ] Crear `RoleAdminForm` para validación
- [ ] Crear `UserRoleAssignForm` para asignación

## 7. Permisos

- [ ] Crear permission class `IsAdminUser` que verifique rol R-ADMIN
- [ ] Aplicar permisos a todas las vistas
- [ ] Actualizar menú del dashboard para nuevo flujo

## 8. Auditoría

- [ ] Crear señal (signal) para registrar cambios en usuarios
- [ ] Crear señal para registrar cambios en roles
- [ ] Crear señal para registrar asignación/revocación de roles

## 9. Pruebas

- [ ] Tests unitarios para vistas de usuarios
- [ ] Tests unitarios para vistas de roles
- [ ] Tests de permisos
- [ ] Tests de integración (crear, editar, asignar rol)

## 10. Verificación

- [ ] Verificar que las vistas cargan correctamente
- [ ] Verificar que los permisos funcionan
- [ ] Verificar que la auditoría registra los cambios
- [ ] Verificar diseño consistente con el resto de la app
