# auth-rbac Specification (CAP-001)

## Purpose

Capa fundacional de auth y autorización del FODEJAS
(`project.md` §7–§8). Cubre **CAP-001**. UI en español;
identificadores en inglés. Tokens JWT: access 15 min,
refresh 7 días, logout tras 30 días de inactividad.

## Requirements

### Requirement: Custom User Model

`accounts.User` MUST extender `AbstractUser` con `documento`
(único, ≥ 6 chars), `email` (único, `USERNAME_FIELD`), `telefono`
(E.164), `fecha_nacimiento` (≥ 14 años). `password` SHALL
hashearse con PBKDF2/Argon2.

#### Scenario: Registro válido

- GIVEN POST `/api/auth/register/` con datos válidos
- WHEN se crea el usuario
- THEN retorna `201` "Registro exitoso. Revise su correo" y
  `is_active=False`

#### Scenario: Email duplicado (anti-enumeración)

- GIVEN un email ya registrado
- WHEN se intenta re-registrar
- THEN retorna `200` mensaje genérico "Si el correo no está
  registrado, recibirá instrucciones"

### Requirement: Catálogo de 13 Roles

MUST sembrarse vía data-migration los 13 roles de `project.md` §7
con `code` (único), `name`, `type` ∈ {interno, externo}.

#### Scenario: Seed de roles

- GIVEN una BD vacía
- WHEN `manage.py migrate`
- THEN `Role.objects.count() == 13`

#### Scenario: Código de rol no permitido

- GIVEN un código fuera de §7
- WHEN R-ADMIN intenta crear el rol
- THEN retorna `400` "El código de rol no está permitido"

### Requirement: Permisos Granulares

Permisos SHALL ser `(app_label, action, convocation_scope
nullable, stage nullable)`. `UserRole(user, role,
convocation_scope nullable)` SHALL permitir el mismo rol con
distinto alcance. `has_perm_for(perm, convocation)` MUST ser el
único chequeo, en `selectors/` y `services/`.

#### Scenario: Permiso scoped por convocatoria

- GIVEN un usuario con R-CT solo en convocatoria X
- WHEN actúa sobre convocatoria Y
- THEN `has_perm_for(...)` retorna `False`

#### Scenario: Permiso denegado se audita

- GIVEN un permiso denegado
- WHEN se rechaza la acción
- THEN se emite `permission_denied` a `apps/audit`

### Requirement: Política de Contraseña Estricta

MUST exigir ≥ 8 chars con una mayúscula, un número y un símbolo.
SHALL NOT aplicar rotación forzada. Hashing MUST ser PBKDF2/Argon2.

#### Scenario: Contraseña válida

- GIVEN una contraseña `Abcdef1!`
- WHEN el validador la evalúa
- THEN retorna éxito y se hashea antes de persistir

#### Scenario: Contraseña inválida

- GIVEN `contraseña` sin mayúscula/número/símbolo
- WHEN se intenta registrar
- THEN retorna `400` con mensaje de política de contraseña

### Requirement: Autenticación JWT

Tokens SHALL emitirse vía `djangorestframework-simplejwt`.
Access **15 min**, refresh **7 días** con renovación deslizante.
Logout MUST añadir el refresh a blacklist; sesión SHALL forzar
logout tras **30 días** de inactividad.

#### Scenario: Login válido

- GIVEN credenciales correctas y email verificado
- WHEN POST `/api/auth/login/`
- THEN retorna `200` con `access`, `refresh` y datos básicos

#### Scenario: Credenciales inválidas

- GIVEN email o contraseña incorrectos
- WHEN POST `/api/auth/login/`
- THEN retorna `401` "Credenciales inválidas" y se emite
  `user_login_failed` a `apps/audit`

#### Scenario: Logout y blacklist

- GIVEN un refresh token válido
- WHEN POST `/api/auth/logout/` con ese refresh
- THEN se añade a blacklist, retorna `205` "Sesión finalizada";
  reusarlo retorna `401`

### Requirement: Registro y Verificación de Email

Aspirantes MUST registrarse antes de radicar FUI. SHALL enviarse
email con token **single-use, TTL 48 h**. La cuenta SHALL NOT
activarse sin verificar el email.

#### Scenario: Verificación exitosa

- GIVEN un token válido dentro de 48 h
- WHEN GET `/api/auth/verify-email/?token=...`
- THEN activa el usuario: "Correo verificado. Ya puede iniciar
  sesión"

#### Scenario: Token expirado

- GIVEN un token con más de 48 h
- WHEN se intenta verificar
- THEN retorna `410` "El enlace expiró"

### Requirement: Reset de Contraseña

Reset SHALL hacerse vía token **single-use, TTL 24 h**. SHALL
responder siempre `200` con mensaje genérico (anti-enumeración).
R-COORD SHALL tener backdoor logged en `apps/audit`.

#### Scenario: Reset solicitado

- GIVEN un email registrado
- WHEN POST `/api/auth/password/reset/` con ese email
- THEN retorna `200` "Si la cuenta existe, recibirá
  instrucciones para restablecer su contraseña"

#### Scenario: Token reutilizado

- GIVEN un token ya consumido
- WHEN se intenta usar de nuevo
- THEN retorna `401` "El enlace ya fue utilizado"
