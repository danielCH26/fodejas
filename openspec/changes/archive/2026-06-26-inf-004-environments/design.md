## Context

FODEJAS es una plataforma Django 5 con PostgreSQL, Redis, Celery y MinIO. Actualmente existe un `.env.example` genérico que no diferencia entre entornos, lo que genera riesgo de configuración incorrecta en staging y producción.

El proyecto sigue la metodología **12-factor app** para configuración, donde las variables de entorno son la fuente única de verdad para configuración.

## Goals / Non-Goals

**Goals:**
- Separar configuración claramente por entorno (dev/staging/prod)
- Crear archivos `.env.example` con valores seguros por defecto
- Mantener secretos fuera del código fuente
- Seguir principio 12-factor: configuración en entorno, no en código
- Facilitar onboarding de nuevos desarrolladores

**Non-Goals:**
- No modificar comportamiento de la aplicación
- No crear infraestructura como código (IaC)
- No implementar deploy automático (ya existe en inf-003-cicd)
- No cambiar el sistema de autenticación o secrets existentes

## Decisions

### 1. Estructura de archivos .env

**Decisión:** Crear archivos `.env.<entorno>.example` por cada entorno.

**Alternativas consideradas:**
- Un solo `.env.example` con comentarios sobre qué valor usar — confuso
- Directorio `environments/` con archivos — más complejo, no estándar Django
- Variables con prefijo `ENV_` — namespace pollution

**Elección:** `.env.<entorno>.example` en raíz del proyecto.

**Justificación:** Estándar python-dotenv, fácil de entender, cada entorno tiene su plantilla.

### 2. Variables sensibles vs no sensibles

**Decisión:** Separar claramente en cada archivo qué valores son sensibles y deben reemplazarse.

**Alternativas consideradas:**
- Todos los valores en un archivo — riesgo de commit accidental de secretos
- Archivos `.env` (sin `.example`) en .gitignore y distribuidos vía secure channel — overhead

**Elección:** Archivos `.env.example` contienen solo valores seguros (no reales secrets).

**Justificación:** Los `.env.example` pueden commitearse. Los `.env` reales (con secrets) se crean localmente y nunca se suben.

### 3. Configuración de Django settings

**Decisión:** Usar `environ` de `django-environ` para lectura de variables de entorno con tipos seguros.

**Alternativas consideradas:**
- `os.environ.get()` directo — propenso a errores de tipo, sin validación
- `python-dotenv` solo — solo carga strings, no valida tipos
- `os.environ` con casting manual — repetitivo

**Elección:** `django-environ` con `environ.Env()`.

**Justificación:** Valida tipos, soporta默认值, integrado con Django, sigue 12-factor.

### 4. Variables requeridas vs opcionales

**Decisión:** Marcar con comentario `# REQUIRED:` las variables obligatorias.

**Alternativas consideradas:**
- Schema de validación — overhead inicial
- Documentación separada — puede desincronizarse

**Elección:** Comentarios en línea `# REQUIRED:` y `# OPTIONAL:`.

**Justificación:** Visible junto a la variable, auto-documentado, fácil de mantener.

### 5. Environments en Django settings

**Decisión:** Usar variable `DJANGO_ENV` para seleccionar el entorno.

**Alternativas consideradas:**
- `DEBUG=True/False` como selector — mezclaba configuración con modo debug
- Múltiples archivos settings (settings/dev.py, settings/staging.py) — duplicación
- Variable `ENVIRONMENT` genérica — menos específico

**Elección:** `DJANGO_ENV=development|staging|production`.

**Justificación:** Explícito, estándar en Django, fácil de verificar en startup.

## Variables por Entorno

### Development (.env.development.example)
```bash
# Django
DEBUG=True
DJANGO_ENV=development
SECRET_KEY=dev-secret-key-not-for-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (local)
DATABASE_URL=postgres://fodejas_user:fodejas_password@localhost:5432/fodejas_db

# Redis (local)
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=  # OPTIONAL

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# MinIO (local)
AWS_ACCESS_KEY_ID=minioadmin
AWS_SECRET_ACCESS_KEY=minioadmin
AWS_STORAGE_BUCKET_NAME=fodejas-media-dev
AWS_S3_ENDPOINT_URL=http://localhost:9000

# Email (console/dev)
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

### Staging (.env.staging.example)
```bash
# Django
DEBUG=False
DJANGO_ENV=staging
SECRET_KEY=  # REQUIRED: generate with django-secretkeygen
ALLOWED_HOSTS=staging.fodejas.gov.co

# Database
DATABASE_URL=  # REQUIRED: from infrastructure

# Redis
REDIS_URL=  # REQUIRED: from infrastructure
REDIS_PASSWORD=  # REQUIRED: from infrastructure

# Celery
CELERY_BROKER_URL=  # REQUIRED: same as REDIS_URL
CELERY_RESULT_BACKEND=  # REQUIRED: same as REDIS_URL

# S3/MinIO (staging)
AWS_STORAGE_BUCKET_NAME=fodejas-media-staging
AWS_S3_ENDPOINT_URL=  # REQUIRED: staging MinIO/S3 endpoint

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=  # REQUIRED: SMTP server
EMAIL_PORT=587
EMAIL_USE_TLS=True
```

### Production (.env.production.example)
```bash
# Django
DEBUG=False
DJANGO_ENV=production
SECRET_KEY=  # REQUIRED: generate with django-secretkeygen (32+ chars)
ALLOWED_HOSTS=fodejas.gov.co,www.fodejas.gov.co

# Database
DATABASE_URL=  # REQUIRED: production PostgreSQL

# Redis
REDIS_URL=  # REQUIRED: production Redis
REDIS_PASSWORD=  # REQUIRED: production Redis password

# Celery
CELERY_BROKER_URL=  # REQUIRED: same as REDIS_URL
CELERY_RESULT_BACKEND=  # REQUIRED: same as REDIS_URL

# S3 (production)
AWS_STORAGE_BUCKET_NAME=fodejas-media-prod
AWS_S3_ENDPOINT_URL=  # REQUIRED: production S3

# Email
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=  # REQUIRED: production SMTP
EMAIL_PORT=587
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=no-reply@fodejas.gov.co
```

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Secretos commiteados accidentalmente | Archivos `.env` en `.gitignore`, solo `.example` en repo |
| Configuración inconsistente entre entornos | Validación con django-environ en startup |
| Valores faltantes en producción | READMEdocumenta variables requeridas con `REQUIRED:` |
| DEBUG=True en producción | Verificación en startup: si `DJANGO_ENV=production` y `DEBUG=True`, error |

## Migration Plan

1. Crear archivos `.env.<entorno>.example` para cada entorno
2. Actualizar `config/settings/base.py` para usar `environ.Env`
3. Agregar validación de `DJANGO_ENV` en settings
4. Actualizar `.gitignore` para incluir `.env` (no solo `.env.*`)
5. Agregar validación en CI: verificar que `DEBUG=False` en staging/production
6. Actualizar README con instrucciones de configuración por entorno
7. Documentar en CONTRIBUTING.md

## Open Questions

1. ¿Usar `django-environ` o `os.environ` con `pydantic` para validación?
   - **Decision:** `django-environ` — integrado con Django, menos overhead
2. ¿Valor por defecto de `SECRET_KEY` en desarrollo?
   - **Decision:** Valor insecure pero funcional en dev, con warning en logs
3. ¿Validación de variables al startup?
   - **Decision:** Sí, con `env.required()` para campos obligatorios
