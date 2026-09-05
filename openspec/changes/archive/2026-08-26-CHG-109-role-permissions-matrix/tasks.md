# Tasks — CHG-109 Matriz de Permisos por Rol

## 1. Agregar URL para la vista de matriz

- [x] Agregar path en `apps/accounts/admin_urls/__init__.py`:
  - `path("permisos/", PermissionMatrixView.as_view(), name="permission_matrix")`

## 2. Crear la vista PermissionMatrixView

- [x] Agregar en `apps/accounts/views/admin_views.py`:
  - Importar modelos Role, Permission, RolePermission
  - Crear clase `PermissionMatrixView(BaseAdminView)`
  - Implementar `get_context_data()` con:
    - Lista de roles
    - Permisos agrupados por app_label
    - Mapping rol → permisos

## 3. Crear el template de matriz

- [x] Crear `apps/accounts/templates/accounts/admin/permissions_matrix.html`
- [x] Estructura de tabla:
  - Header: celda "Rol" + permisos por app
  - Filas: nombre del rol + celdas con estado de permiso
- [x] Estilos consistentes con el admin de cuentas

## 4. Agregar restricción de acceso

- [x] Restringir acceso solo a usuarios con rol R-ADMIN (heredado de BaseAdminView)
- [x] Verificar que usuarios sin R-ADMIN reciban redirect

## 5. Agregar enlace en el menú de admin

- [x] Agregar enlace a la matriz en el sidebar del admin
- [x] Archivo: `apps/accounts/templates/accounts/admin/admin_base.html`

## 6. Pruebas

- [x] Test unitario: verificar contexto de vista
- [x] Test de acceso: R-ADMIN puede ver, otros roles no
- [x] Test de integración: matriz muestra datos correctos

## 7. Verificación

- [x] La matriz carga correctamente
- [x] Muestra todos los roles
- [x] Muestra todos los permisos agrupados por app
- [x] Indica correctamente qué permisos tiene cada rol
- [x] Acceso restringido a R-ADMIN
