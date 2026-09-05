# Delta Spec — CHG-109: Matriz de Permisos por Rol

## MODIFIED

### accounts/admin_views.py

ADD: `PermissionMatrixView` class

```python
class PermissionMatrixView(BaseAdminView):
    """Vista de matriz de permisos por rol."""
    template_name = "accounts/admin/permissions_matrix.html"
    admin_section = "permissions"

    def get_context_data(self, **kwargs):
        # Obtiene roles activos, permisos agrupados por app,
        # y mapping rol->permisos para renderizar la matriz
```

### accounts/admin_urls/admin.py

ADD: URL path para la matriz de permisos

```python
path("permisos/", admin_views.PermissionMatrixView.as_view(), name="permission_matrix"),
```

### accounts/templates/admin/

ADD: `permissions_matrix.html` — Template de la matriz de permisos

- Tabla con roles en filas, permisos en columnas
- Permisos agrupados por app_label
- Iconos de verificación para permisos activos

### accounts/templatetags/

ADD: `matrix_tags.py` — Template tags para la matriz

- `get_item` filter para acceder a diccionarios en templates

### accounts/templates/admin/admin_base.html

ADD: Enlace a la matriz de permisos en el sidebar

```html
<a href="{% url 'accounts_admin:permission_matrix' %}" ...>
    <i class="bi bi-grid me-2"></i>Matriz de Permisos
</a>
```

## SHALL

- La vista solo es accesible para usuarios con rol `R-ADMIN` (heredado de `BaseAdminView`)
- La matriz muestra todos los roles activos del sistema
- La matriz agrupa permisos por app_label
- La matriz indica visualmente qué permisos tiene cada rol
- El diseño es consistente con el resto del admin de cuentas
