# Design: CHG-101-auth-rbac — Autenticación, Roles y Permisos (CAP-001)

## Enfoque Técnico

Capa fundacional de auth + RBAC en `apps/accounts/` (hoy vacía). `User(AbstractUser)`
con `email` como `USERNAME_FIELD`; roles y permisos como **modelos de primera clase**
(Opción D de `explore.md`) para hacer explícito el alcance por convocatoria/etapa.
JWT vía `djangorestframework-simplejwt` (access 15 min, refresh 7 d, blacklist al
logout, inactividad 30 d). UI en español con Bootstrap 5 + Crispy Forms. Cubre los
8 requisitos de `specs/auth-rbac/spec.md`. Los chequeos de permiso viven **solo** en
`selectors/`/`services/` (AGENTS.md §6); las vistas son delgadas.

## Decisiones de Arquitectura

### Decision: Modelo de Usuario base

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| `AbstractUser` | Reusa username/password/email/first_name/last_name/is_staff/is_active/is_superuser/last_login/date_joined/groups/user_permissions + integración admin; `USERNAME_FIELD="email"` es patrón documentado. Solo se agregan `documento`, `telefono`, `fecha_nacimiento`. | ✅ Elegida |
| `AbstractBaseUser` | Control total pero obliga a reimplementar todos los campos estándar y `BaseUserManager`; solo vale la pena si se eliminan campos por defecto o se cambia radicalmente el flujo de auth. | Rechazada — sobre-ingeniería |

**Racional**: AbstractUser preserva la integración con admin y señales (`user_logged_in`,
`user_login_failed`) que `apps/audit` consumirá. Email como `USERNAME_FIELD` + `REQUIRED_FIELDS=["documento", "first_name", "last_name"]`.

### Decision: Modelado de Roles y Permisos

| Opción | Tradeoff | Decisión |
|--------|----------|----------|
| `Role`/`Permission` de primera clase + `UserRole`/`RolePermission` through | Alcance por convocatoria/etapa explícito y auditable; un usuario puede tener R-COORD global y R-CT en convocatoria X. | ✅ Elegida |
| Django `Group` nativo | No expresa `convocation_scope` ni `stage`; explotaría un Group por convocatoria×etapa. | Rechazada — no granular |

**Racional**: `Permission(app_label, action, convocation_scope nullable, stage nullable)`
+ `RolePermission` M2M. `UserRole(user, role, convocation_scope nullable)` es el *through*
que permite el mismo rol con distinto alcance. `Groups` se conserva solo para el admin de
Django (mapeo 1:1 con `Role` para compatibilidad). Seed de 13 roles vía data-migration
(`project.md` §7.1): 9 internos (R-COORD, R-CT, R-JUNTA, R-PRES, R-SECEDU, R-TESOR,
R-OFIJUR, R-CONTROL, R-ADMIN) y 4 externos (R-ASPIRANTE, R-BENEF, R-CIUDA, R-AUDITOR).

### Decision: Ciclo de vida del token JWT

**Elección**: `SIMPLE_JWT` con `access 15 min`, `refresh 7 d`, `ROTATE_REFRESH_TOKENS=True`,
`BLACKLIST_AFTER_ROTATION=True`, logout añade el refresh a blacklist. Hard logout tras
30 d de inactividad: campo `last_activity` en `User`, validado en un
`RefreshToken`-serializer custom antes de emitir el nuevo access.

```python
# config/settings.py
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": secrets.get_required("JWT_SIGNING_KEY"),
    "AUTH_HEADER_TYPES": ("Bearer",),
}
```

`JWT_SIGNING_KEY` vía `apps/core/secrets.py` (ya existe `EnvSecretStore`).

### Decision: Política de contraseña estricta

**Elección**: validador custom `FodejasPasswordValidator` (min 8, ≥1 mayúscula, ≥1
dígito, ≥1 símbolo), agregado a `AUTH_PASSWORD_VALIDATORS`. **Sin rotación forzada**
(req. spec). Hashing PBKDF2 (default Django 5); Argon2 queda como mejora futura opcional
(`argon2-cffi`) — fuera de alcance de este change. Mensajes de error en español.

```python
# apps/accounts/validators.py
class FodejasPasswordValidator:
    def validate(self, password, user=None): ...   # 8 chars, upper, digit, symbol
    def get_help_text(self): return "Mínimo 8 caracteres con mayúscula, número y símbolo."
```

### Decision: UI con Bootstrap 5 + Crispy Forms

**Elección**: `django-crispy-forms` + `crispy-bootstrap5`. Paleta del sistema
(`primary #003366`, `accent #28A745`, `background #FAFBFC`) en un `base.html` con
CSS custom. Plantillas en `apps/accounts/templates/accounts/` con labels en español.
El API (JWT) y las vistas HTML coexisten; las vistas web renderizan formularios Crispy
y, al submit exitoso, redirigen o muestran mensajes.

## Flujo de Datos

```
Cliente ──POST /api/auth/login/──▶ LoginView ──▶ serializers.EmailLoginSerializer
   │                                     │              │
   │                                     │              ▼
   │                                     │        authenticate(email, password)
   │                                     │              │
   │                                     │      ┌───────┴────────┐
   │                                     │      ▼                ▼
   │                                     │  TokenPair       apps/audit
   │                                     │  (access,refresh)  signal(user_logged_in)
   │                                     ◀──────────────┘
   │◀── 200 {access, refresh, user} ────┘
   │
   ├──GET /api/auth/me/ ──Authorization: Bearer ──▶ JWTAuthentication ──▶ MeView
   │
   └──Permiso en endpoint downstream ──▶ services/xxx.has_perm_for(perm, convocation)
                                            │
                                            ▼
                                  selectors/has_perm_for
                                  (cache Redis 5 min: user_id,conv_id → perms)
                                            │
                                            └──▶ permission_denied signal si False
```

## Cambios de Archivos

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `apps/accounts/models.py` | Crear | `User(AbstractUser)` (documento, email unique, telefono, fecha_nacimiento, last_activity), `Role`, `Permission`, `UserRole`, `RolePermission`, `EmailVerificationToken`, `PasswordResetToken` |
| `apps/accounts/validators.py` | Crear | `FodejasPasswordValidator` (8 chars, mayúscula, dígito, símbolo) |
| `apps/accounts/selectors.py` | Crear | `has_perm_for(user, perm, convocation=None, stage=None)` — único punto de chequeo |
| `apps/accounts/services.py` | Crear | `register_aspirante`, `verify_email`, `request_password_reset`, `reset_password`, `logout` (blacklist) |
| `apps/accounts/serializers.py` | Crear | `RegisterSerializer`, `EmailLoginSerializer`, `MeSerializer`, `PasswordResetSerializer` |
| `apps/accounts/views.py` | Crear | `LoginView`, `RefreshView`, `LogoutView`, `RegisterView`, `VerifyEmailView`, `PasswordResetView`, `MeView` (vistas delgadas) |
| `apps/accounts/urls.py` | Crear | `/api/auth/{login,refresh,logout,register,verify-email,password/reset,me}/` |
| `apps/accounts/admin.py` | Crear | Registro admin de User/Role/Permission |
| `apps/accounts/apps.py` | Modificar | `ready()` conecta señales a `apps/audit` |
| `apps/accounts/migrations/0001_initial.py` | Crear | Esquema inicial de models |
| `apps/accounts/migrations/0002_seed_roles.py` | Crear | Data-migration: 13 roles de §7.1 |
| `apps/accounts/templates/accounts/base.html` | Crear | Bootstrap 5 + paleta FODEJAS |
| `apps/accounts/templates/accounts/{login,register,verify,reset}*.html` | Crear | Formularios Crispy, UI español |
| `apps/audit/signals.py` | Crear | Consumidores de `user_logged_in`, `user_login_failed`, `user_registered`, `permission_denied` (propuesta dice "Modify" pero el archivo no existe) |
| `apps/core/logging_config.py` | Modificar | Añadir enmascarador PII (documento/email/telefono) al `JSONFormatter` |
| `config/settings.py` | Modificar | `AUTH_USER_MODEL="accounts.User"`, `REST_FRAMEWORK`, `SIMPLE_JWT`, `AUTH_PASSWORD_VALIDATORS` (+ custom), `CRISPY_ALLOWED_TEMPLATE_PACKS`, `CRISPY_TEMPLATE_PACK="bootstrap5"` |
| `config/urls.py` | Modificar | `path("api/auth/", include("apps.accounts.urls"))` |
| `pyproject.toml` | Modificar | `+djangorestframework-simplejwt[crypto]>=5.3`, `+django-crispy-forms>=2.1`, `+crispy-bootstrap5>=2024.2` |
| `apps/accounts/tests/` | Crear | factories, test_models, test_jwt, test_selectors, test_register, test_reset |

## Interfaces / Contratos

```python
# apps/accounts/selectors.py — único chequeo de permiso (AGENTS.md §6)
def has_perm_for(
    user: User,
    perm: str,                       # "app_label.action" ej "applications.add_application"
    convocation: int | None = None,
    stage: str | None = None,
) -> bool: ...

# apps/accounts/models.py
class Role(models.Model):
    code = models.CharField(max_length=16, unique=True)   # "R-ASPIRANTE"
    name = models.CharField(max_length=80)                 # "Aspirante"
    type = models.CharField(max_length=8)                  # interno | externo
    class Meta: constraints = [CheckConstraint(type__in=("interno","externo"), name="role_type_valid")]

class Permission(models.Model):
    app_label = models.CharField(max_length=100)          # "applications"
    action = models.CharField(max_length=50)              # "add_application"
    convocation_scope = models.ForeignKey("convocatories.Convocatory", null=True, ...)
    stage = models.CharField(max_length=30, null=True)    # nullable

class UserRole(models.Model):
    user = models.ForeignKey(User, related_name="user_roles", ...)
    role = models.ForeignKey(Role, ...)
    convocation_scope = models.ForeignKey("convocatories.Convocatory", null=True, ...)

class RolePermission(models.Model):
    role = models.ForeignKey(Role, related_name="role_permissions", ...)
    permission = models.ForeignKey(Permission, ...)
```

## Estrategia de Pruebas

| Capa | Qué se prueba | Enfoque |
|------|---------------|---------|
| Unit | Seed 13 roles (`count==13`, códigos §7); `has_perm_for` scoped (R-CT en X no en Y); `FodejasPasswordValidator` (válida/inválida); validador de documento/email | `pytest` + `factory_boy`, fixtures sintéticos |
| Integration | Login válido → 200+token; credenciales inválidas → 401+`user_login_failed`; logout → blacklist, reúso → 401; registro → 201 `is_active=False`; verificación email 48h (válida/expirada 410); reset 24h single-use (200 genérico anti-enumeración, reúso 401) | `pytest-django`, APIClient, sin red real |
| E2E | Fuera de alcance (config `e2e: false`) | — |

## Migración / Rollout

BD vacía (sin usuarios transaccionales): `manage.py migrate` crea `0001_initial` +
seed 13 roles. Sin `AUTH_USER_MODEL` previo → no hay migración de usuario legacy.
Rollback (propuesta §Rollback): `git revert` → `migrate accounts zero` → desactivar
flag. **No requiere feature flag** porque CAP-001 se entrega antes que cualquier dato
de usuario downstream.

## Preguntas Abiertas

- [ ] `convocatories.Convocatory` aún no existe (CAP-002) — `Permission.convocation_scope`/`UserRole.convocation_scope` usan FK *string* lazy; la migración 0001 no falla si la app convocatories no tiene modelo, pero el FK queda pendiente hasta CAP-002. Confirmar si se modela como FK lazy o como `IntegerField` desacoplado por ahora.
- [ ] Proveedor de email (SMTP) — el proposal deja el proveedor concreto fuera de alcance; el servicio usa un backend console en dev. Confirmar interfaz del sender para no acoplar.
