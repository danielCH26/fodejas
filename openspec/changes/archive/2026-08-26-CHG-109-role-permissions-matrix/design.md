# Design: CHG-109 Matriz de Permisos por Rol

## Overview

Crear una vista de matriz de permisos que muestre la relación entre roles y permisos del sistema de forma tabular.

## Arquitectura

### Componentes

1. **View**: `PermissionMatrixView` — renders la matriz
2. **Template**: `permissions_matrix.html` — tabla de permisos
3. **URL**: `/accounts/admin/permisos/`

### Flujo de datos

```
PermissionMatrixView
    └── Obtiene todos los Role.objects.all()
    └── Obtiene todos los Permission.objects.all() grouped by app_label
    └── Obtiene RolePermission para construir mapping rol→permisos
    └── Renderiza template con contexto
```

### Estructura del contexto del template

```python
{
    "roles": QuerySet<Role>,
    "permissions_by_app": {
        "accounts": [Permission, ...],
        "convocatories": [Permission, ...],
        ...
    },
    "role_permissions": {
        role_id: {permission_id: True/False, ...},
        ...
    }
}
```

## Implementación

### 1. Vista

**Archivo**: `apps/accounts/views/admin_views.py`

```python
class PermissionMatrixView(TemplateView):
    """Vista de matriz de permisos por rol."""
    template_name = "accounts/admin/permissions_matrix.html"

    def get_context_data(self, **kwargs):
        # Obtener roles
        roles = Role.objects.filter(is_active=True).order_by('codigo')

        # Obtener permisos agrupados por app
        permissions = Permission.objects.all()
        permissions_by_app = {}
        for perm in permissions:
            app = perm.content_type.app_label
            if app not in permissions_by_app:
                permissions_by_app[app] = []
            permissions_by_app[app].append(perm)

        # Obtener permisos por rol
        role_permissions = {}
        for role in roles:
            perms = RolePermission.objects.filter(role=role).select_related('permission')
            role_permissions[role.id] = {rp.permission_id: True for rp in perms}

        return {
            "roles": roles,
            "permissions_by_app": permissions_by_app,
            "role_permissions": role_permissions,
        }
```

### 2. URLs

**Archivo**: `apps/accounts/admin_urls/admin.py`

```python
path("permisos/", admin_views.PermissionMatrixView.as_view(), name="permission_matrix"),
```

### 3. Template

**Archivo**: `apps/accounts/templates/accounts/admin/permissions_matrix.html`

- Tabla con:
  - Header: "Rol" + lista de permisos (agrupados por app)
  - Filas: cada rol con celdas indicando si tiene permiso
  - Usa icons (✓/✗) o checkboxes deshabilitados

### 4. Permisos

- Solo usuarios con rol `R-ADMIN` pueden acceder
- Mixin `PermissionRequiredMixin` o decorator `@login_required` + verificación de rol

### 5. Auditoría

- Registrar acceso a la vista en bitácora (opcional, si hay cambios reales)

## Consideraciones de UI/UX

- La tabla puede ser muy ancha si hay muchos permisos
- Soluciones:
  - Scroll horizontal
  - Paginación por app
  - Filtros por app

## Testing

- Unit test: verificar contexto tiene datos correctos
- Integration: verificar acceso con R-ADMIN y sin él
- Template: verificar renderizado de tabla

## Fuera del alcance (para futuro)

- Edición inline de permisos desde la matriz
- Exportación
- Búsqueda/filtrado avanzado
