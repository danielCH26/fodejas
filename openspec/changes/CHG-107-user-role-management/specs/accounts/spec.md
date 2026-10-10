# SPEC — CHG-107: Gestión de Usuarios, Roles y Permisos

## ADDED

### Vistas HTML de Administración

Se agregaron las siguientes vistas en `apps/accounts/views/admin.py`:

#### User Management Views

- `UserListView` — Lista usuarios con filtros por rol, estado, búsqueda por documento/email
- `UserCreateView` — Crea usuario con validación de documento y email únicos
- `UserUpdateView` — Edita datos de usuario
- `UserDetailView` — Muestra detalle con historial de roles y actividad
- `UserToggleActiveView` — Activa/Desactiva usuario (soft delete)

#### Role Management Views

- `RoleListView` — Lista todos los roles del sistema
- `RoleCreateView` — Crea nuevo rol
- `RoleUpdateView` — Edita rol existente
- `RoleDetailView` — Muestra rol con usuarios asignados

#### Role Assignment Views

- `UserRoleAssignView` — Asigna rol a usuario con scope opcional de convocatoria
- `UserRoleRevokeView` — Revoca rol de usuario

### URLs

Se agregaron las siguientes rutas en `apps/accounts/urls/admin.py`:

| URL | Vista | Descripción |
|-----|-------|-------------|
| `/accounts/admin/users/` | UserListView | Listado de usuarios |
| `/accounts/admin/users/crear/` | UserCreateView | Crear usuario |
| `/accounts/admin/users/<id>/` | UserDetailView | Ver detalle usuario |
| `/accounts/admin/users/<id>/editar/` | UserUpdateView | Editar usuario |
| `/accounts/admin/users/<id>/toggle/` | UserToggleActiveView | Activar/Desactivar |
| `/accounts/admin/roles/` | RoleListView | Listado de roles |
| `/accounts/admin/roles/crear/` | RoleCreateView | Crear rol |
| `/accounts/admin/roles/<id>/` | RoleDetailView | Ver rol |
| `/accounts/admin/roles/<id>/editar/` | RoleUpdateView | Editar rol |
| `/accounts/admin/users/<id>/roles/` | UserRoleAssignView | Asignar roles |
| `/accounts/admin/users/<id>/roles/<role_id>/revocar/` | UserRoleRevokeView | Revocar rol |

### Permissions

Se agregó permission class `IsAdminRole` en `apps/accounts/permissions.py`:

```python
class IsAdminRole(permissions.BasePermission):
    """Permission that requires user to have R-ADMIN role."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.user_roles.filter(role__code='R-ADMIN').exists()
```

### Templates

Se crearon los siguientes templates en `apps/accounts/templates/accounts/admin/`:

- `admin_base.html` — Template base para vistas de admin
- `users/list.html` — Listado de usuarios con filtros
- `users/form.html` — Formulario de usuario (crear/editar)
- `users/detail.html` — Detalle de usuario con historial
- `roles/list.html` — Listado de roles
- `roles/form.html` — Formulario de rol
- `roles/detail.html` — Detalle de rol con usuarios

### Forms

Se crearon los siguientes formularios en `apps/accounts/forms/admin.py`:

- `UserAdminForm` — Validación para creación/edición de usuarios
- `RoleAdminForm` — Validación para roles
- `UserRoleAssignForm` — Asignación de roles con scope opcional

### Signals de Auditoría

Se crearon señales para registrar cambios:

- `user_created` — Usuario creado
- `user_updated` — Usuario modificado
- `user_deactivated` — Usuario desactivado
- `role_created` — Rol creado
- `role_updated` — Rol modificado
- `role_assigned` — Rol asignado a usuario
- `role_revoked` — Rol revocado de usuario

## MODIFIED

### apps/accounts/views.py

Se modificaron las siguientes vistas para usar el nuevo sistema de permisos:

- `DashboardView` — Actualizado para usar `IsAdminRole` en lugar de `IsAdminUser`

### apps/accounts/urls.py

Se modificó para incluir las nuevas rutas de administración:

```python
path("admin/", include("apps.accounts.urls.admin")),
```

## RENAMED

Ninguno.

## REMOVED

Ninguno.
