# CHG-107: Gestión de Usuarios, Roles y Permisos con Vistas Propias

## Contexto

Actualmente, la gestión de usuarios y roles utiliza el Django Admin (`/admin/`) que:
- No está alineado con la experiencia de usuario del proyecto
- Expone funcionalidades de superuser que no deberían estar disponibles para administradores de aplicación
- No permite personalización del flujo de negocio
- No integra con las notificaciones internas del sistema

Se requiere una interfaz de administración propia usando Django Templates + HTMX que permita:
- CRUD completo de usuarios con validación de negocio
- Asignación de roles por usuario
- Gestión de roles y permisos
- Auditoría de cambios en la gestión de usuarios

## Capacidades afectadas

- **CAP-001** — Autenticación y Gestión de Usuarios/Roles
- **CAP-022** — Bitácora de Auditoría

## Reglas de negocio afectadas

- project.md §7 — Roles del sistema (R-ADMIN, R-COORD, R-CT, etc.)
- project.md §7.1 — Roles de la plataforma con descripción de cada uno
- project.md §11.1 — Requisitos mínimos para usuarios del sistema

## Cambios propuestos

> **NOTA**: Este change NO modifica el Django Admin (`/admin/`). El Django Admin queda intacto y disponible únicamente para superusuarios (is_superuser=True). Todas las funcionalidades de gestión de usuarios y roles se implementan en vistas propias independientes que no tocan el admin de Django.

### 1. Vistas de Gestión de Usuarios

Crear vistas Django Template para:
- Listado de usuarios con filtros (por rol, estado, fecha de creación)
- Crear usuario con validación de documento único y email único
- Editar usuario (datos personales, estado, cambiar contraseña)
- Ver detalle de usuario con historial de roles y actividad
- Desactivar/Activar usuario (soft delete)
- Buscar usuario por documento o email

### 2. Vistas de Gestión de Roles

Crear vistas Django Template para:
- Listado de roles del sistema
- Crear/Editar rol con nombre, código, tipo (interno/externo), descripción
- Ver qué usuarios tienen asignado cada rol
- CRUD de permisos granulares (app_label, action, scope, stage)

### 3. Vistas de Asignación de Roles

- Listado de usuarios con sus roles actuales
- Asignar/Revocar rol a usuario
- Asignar rol con scope de convocatoria específico
- Historial de cambios de roles por usuario

### 4. Integración con Auditoría

- Toda acción de creación, modificación o eliminación queda registrada
- Se incluye el usuario que realizó el cambio
- Se registra el valor anterior y nuevo

### 5. Permisos de Acceso

Solo pueden acceder a estas vistas:
- Usuarios con rol `R-ADMIN` (acceso total)
- El sistema no permite acceso desde Django Admin para estas funciones

## Criterios de aceptación

- [ ] Las vistas de gestión de usuarios cargan y muestran el listado correctamente
- [ ] Se puede crear un nuevo usuario con datos válidos
- [ ] Se puede editar un usuario existente
- [ ] Se puede activar/desactivar un usuario
- [ ] Las vistas de gestión de roles muestran todos los roles del sistema
- [ ] Se puede crear un nuevo rol
- [ ] Se puede asignar un rol a un usuario
- [ ] Se puede revocar un rol de un usuario
- [ ] Toda acción queda registrada en la bitácora de auditoría
- [ ] Los permisos restrictivos funcionan (solo R-ADMIN)
- [ ] El diseño es consistente con el resto de la aplicación

## Pruebas

- Pruebas unitarias para las vistas de gestión
- Pruebas de integración para flujos de creación y edición
- Pruebas de permisos para verificar acceso solo a R-ADMIN

## Riesgos y fuera del alcance

### Riesgos
- Mantener sincronización entre el modelo UserRole y las vistas
- Performance al listar usuarios con muchos roles

### Fuera del alcance
- Integración con sistemas externos de autenticación (LDAP, SSO)
- Dashboard analítico de usuarios (futuro change)
- Envío de emails de notificación (ya existe en CAP-019)
