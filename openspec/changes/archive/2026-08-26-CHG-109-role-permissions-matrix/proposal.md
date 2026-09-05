# CHG-109: Matriz de Permisos por Rol

## Contexto

Actualmente, la gestión de roles y permisos en la plataforma FODEJAS está分散ada en múltiples vistas. Los administradores no tienen una visión consolidada de qué permisos tiene cada rol. Se requiere una vista de "matriz de permisos" que muestre de forma clara y tabular qué permisos (acciones) están asignados a cada rol del sistema.

Esta matriz es necesaria para:
- Auditoría visual de permisos del sistema
- Facilitar la gestión de roles por parte de R-ADMIN
- Cumplimiento normativo (trazabilidad de permisos)

## Capacidades afectadas

- **CAP-001** — Autenticación y Gestión de Usuarios/Roles
- **CAP-022** — Bitácora de Auditoría

## Reglas de negocio afectadas

- project.md §7 — Roles del sistema (R-ADMIN, R-COORD, R-CT, etc.)
- project.md §7.2 — Permisos granulares (app_label, action, scope, stage)

## Cambios propuestos

### 1. Vista de Matriz de Permisos

Crear una vista Django Template que muestre:
- Filas: Roles del sistema (Role)
- Columnas: Permisos (Permission) agrupados por app_label
- Celdas: Checkbox o indicador visual de si el rol tiene el permiso

### 2. Modelo de Datos

No se requieren cambios en modelos. La matriz se construye a partir de:
- `accounts.Role` — roles existentes
- `accounts.Permission` — permisos existentes
- `accounts.RolePermission` — relación muchos a muchos

### 3. Vistas y URLs

- GET `/accounts/admin/permisos/` — Matriz de permisos (solo R-ADMIN)
- Posibilidad de filtro por app_label

### 4. Template

- Tabla HTML con headers de permisos
- Filas de roles con checkboxes o iconos
- Diseño consistente con resto del admin

### 5. Integración con Auditoría

- Registrar acceso a la matriz de permisos

## Criterios de aceptación

- [ ] La matriz muestra todos los roles del sistema
- [ ] La matriz muestra todos los permisos agrupados por app
- [ ] La matriz indica correctamente qué permisos tiene cada rol
- [ ] Solo usuarios con R-ADMIN pueden acceder
- [ ] El diseño es consistente con el admin de cuentas

## Pruebas

- Tests unitarios del template de matriz
- Tests de integración para verificar permisos
- Tests de acceso (solo R-ADMIN)

## Riesgos y fuera del alcance

### Riesgos
- Performance con muchos permisos y roles (requiere paginación si es necesario)

### Fuera del alcance
- Edición de permisos desde la matriz (futuro change)
- Exportación a PDF/Excel (futuro change)
