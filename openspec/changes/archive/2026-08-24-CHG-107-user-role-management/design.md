# Design — CHG-107: Gestión de Usuarios, Roles y Permisos

> **IMPORTANTE**: Este change NO modifica el Django Admin (`/admin/`) de Django. El Django Admin queda intacto y disponible únicamente para superusuarios del sistema (is_superuser=True). Todas las funcionalidades de gestión de usuarios y roles se implementan en vistas propias independientes.

## 1. Arquitectura de Vistas

### 1.1 Estructura de URLs

```
/accounts/admin/
├── users/
│   ├── (list)                    GET     - UserListView
│   ├── crear/                    GET/POST - UserCreateView
│   ├── <id>/                     GET     - UserDetailView
│   ├── <id>/editar/              GET/POST - UserUpdateView
│   ├── <id>/toggle/              POST    - UserToggleActiveView
│   └── <id>/roles/              GET/POST - UserRoleAssignView
│       └── <role_id>/revocar/    POST    - UserRoleRevokeView
│
└── roles/
    ├── (list)                    GET     - RoleListView
    ├── crear/                    GET/POST - RoleCreateView
    ├── <id>/                     GET     - RoleDetailView
    └── <id>/editar/              GET/POST - RoleUpdateView
```

### 1.2 Herencia de Vistas

Todas las vistas de admin heredan de una clase base con funcionalidades comunes:

```python
class BaseAdminView(LoginRequiredMixin, PermissionMixin, TemplateView):
    """Base view for admin pages."""
    permission_required = 'R-ADMIN'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin_section'] = self.admin_section
        return context
```

### 1.3 Patrón de Formularios

Se utiliza el patrón estándar de Django:
- `FormView` para formularios simples
- `CreateView`/`UpdateView` para modelos
- Validación en el método `clean()` del form

## 2. Modelo de Datos

### 2.1 User (CustomUser)

Ya existe en `apps/accounts/models.py`. Campos relevantes para admin:
- `email` — único, identificador de login
- `documento` — único, documento de identidad
- `first_name`, `last_name` — nombre completo
- `is_active` — para soft delete
- `is_staff` — acceso al admin de Django
- `is_superuser` — superusuario
- `date_joined` — fecha de creación
- `last_login` — último ingreso

### 2.2 UserRole

Relación muchos a muchos entre usuarios y roles con scope opcional:

```python
class UserRole(models.Model):
    user = ForeignKey(CustomUser)
    role = ForeignKey(Role)
    convocation_scope_id = CharField(null=True, blank=True)  # opcional
    created_at = DateTimeField(auto_now_add=True)
```

### 2.3 Role

```python
class Role(models.Model):
    code = CharField(max_length=16, unique=True)  # ej: R-ADMIN
    name = CharField(max_length=80)
    type = CharField(choices=[('interno', 'Interno'), ('externo', 'Externo')])
    description = TextField(blank=True)
```

### 2.4 Permission

Permisos granulares por app y acción:

```python
class Permission(models.Model):
    app_label = CharField(max_length=100)
    action = CharField(max_length=50)
    convocation_scope_id = CharField(null=True, blank=True)
    stage = CharField(max_length=30, null=True, blank=True)
```

### 2.5 RolePermission

Asociación muchos a muchos entre roles y permisos:

```python
class RolePermission(models.Model):
    role = ForeignKey(Role)
    permission = ForeignKey(Permission)
```

## 3. Permisos

### 3.1 Permission Class Principal

```python
class IsAdminRole(BasePermission):
    """
    Verifica que el usuario tenga el rol R-ADMIN.
    
    Diferencia con IsAdminUser:
    - IsAdminUser verifica is_staff o is_superuser
    - IsAdminRole verifica user_roles con role__code='R-ADMIN'
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.user_roles.filter(role__code='R-ADMIN').exists()
```

### 3.2 Hierarchy de Permisos

```
R-ADMIN (Administrador del Sistema)
├── Acceso total a gestión de usuarios
├── Acceso total a gestión de roles
├── Acceso total a configuración del sistema
│
R-COORD (Coordinador Técnico)
├── Gestión de convocatorias
├── Revisión de postulaciones
│
R-CT (Comité Técnico)
├── Evaluación de postulaciones
│
R-TESORERO
├── Gestión de pagos
│
R-ASPIRANTE (Aspirante/Beneficiario)
└── Solo acceso a su perfil y postulaciones
```

## 4. Diseño de Templates

### 4.1 Estructura Base

```
admin_base.html
├── {% include 'admin/header.html' %}
├── {% block admin_content %}
│   └── Contenido específico
└── {% include 'admin/sidebar.html' %}
```

### 4.2 Componentes Reutilizables

- `admin/table.html` — Tabla con paginación y filtros
- `admin/form.html` — Formulario estándar
- `admin/breadcrumb.html` — Navegación
- `admin/modal.html` — Confirmaciones
- `admin/toast.html` — Mensajes de éxito/error

### 4.3 Diseño Responsive

- Mobile-first con Bootstrap 5
- Sidebar colapsable en móviles
- Tablas scrollables horizontalmente

## 5. Auditoría

### 5.1 Modelo de Eventos

Cada acción genera un registro en la bitácora:

```python
# Ejemplo de señal
@receiver(post_save, sender=CustomUser)
def log_user_change(sender, instance, created, **kwargs):
    action = 'created' if created else 'updated'
    AuditLog.objects.log(
        user=instance,
        action=f'user_{action}',
        details={
            'email': instance.email,
            'documento': instance.documento,
        },
        actor=get_current_user()  # quien realizó el cambio
    )
```

### 5.2 Eventos a Registrar

| Evento | Descripción | Actor |
|--------|-------------|-------|
| `user_created` | Usuario creado | Admin que lo creó |
| `user_updated` | Usuario modificado | Admin que lo editó |
| `user_deactivated` | Usuario desactivado | Admin que lo desactivó |
| `role_created` | Rol creado | Admin que lo creó |
| `role_assigned` | Rol asignado a usuario | Admin que lo asignó |
| `role_revoked` | Rol removido de usuario | Admin que lo removió |

## 6. Flujos de Usuario

### 6.1 Crear Usuario

1. Admin accede a `/accounts/admin/users/crear/`
2. Completa formulario:
   - Email (único)
   - Documento (único, 6+ caracteres)
   - Nombres y Apellidos
   - Teléfono (opcional)
   - Fecha de nacimiento (opcional)
3. Sistema valida uniqueness
4. Sistema crea usuario con contraseña temporal
5. Sistema registra en auditoría
6. Redirige a detalle del usuario

### 6.2 Asignar Rol

1. Admin accede a `/accounts/admin/users/<id>/roles/`
2. Selecciona rol de la lista
3. (Opcional) Selecciona scope de convocatoria
4. Confirma asignación
5. Sistema crea UserRole
6. Sistema registra en auditoría
7. Muestra mensaje de éxito

## 7. Excepciones y Edge Cases

### 7.1 Validaciones

| Caso | Comportamiento |
|------|----------------|
| Email duplicado | Error en form, mensaje específico |
| Documento duplicado | Error en form, mensaje específico |
| Último admin desactiva | Advertir, requerir confirmación |
| Asignar rol ya existente | Ignorar o actualizar scope |
| Revocar último rol | Permitir, usuario sin acceso |

### 7.2 Permisos

| Caso | Comportamiento |
|------|----------------|
| Usuario sin R-ADMIN intenta acceder | 403 Forbidden |
| Usuario no autenticado | Redirigir a login |
| Usuario inactivo intenta acceder | Redirigir a login con mensaje |

## 8. Integración con Componentes Existentes

### 8.1 Dashboard Actual

El dashboard ya tiene navegación a `/admin/` que ahora apuntará a las nuevas vistas.

### 8.2 Notificaciones

Las acciones de admin pueden generar notificaciones al usuario afectado (futuro).

### 8.3 Auditoría

Se reutiliza el modelo existente de auditoría en `apps/audit/`.

## 9. Pruebas

### 9.1 Tests Unitarios

- `test_user_list_view` — Verifica que lista usuarios
- `test_user_create_view` — Verifica creación con datos válidos
- `test_user_create_duplicate_email` — Verifica error con email duplicado
- `test_role_assignment` — Verifica asignación de rol
- `test_permission_denied` — Verifica 403 sin R-ADMIN

### 9.2 Tests de Integración

- `test_admin_workflow` — Flujo completo: crear usuario, asignar rol, verificar acceso
- `test_audit_logging` — Verifica que se registran los eventos

## 10. Pendientes de Decision

| Decisión | Opciones | Recomendación |
|----------|----------|---------------|
| Contraseña temporal | Auto-generada vs. Email vs. Primera vez login | Auto-generada, cambio obligatorio |
| Notificaciones | Email vs. Interna vs. Ambas | Internas (CAP-019) |
| Sesiones | JWT vs. Session | Session (más simple) |
