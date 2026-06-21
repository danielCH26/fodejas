## Context

El proyecto FODEJAS requiere establecer la infraestructura básica del repositorio antes de comenzar el desarrollo de las capacidades funcionales. Esta configuración sienta las bases para un desarrollo organizado, mantenible y seguro.

**Stack confirmado** (project.md §4):
- Django 5.x + Django REST Framework
- PostgreSQL 16, Redis + Celery
- Docker + GitHub Actions
- WeasyPrint, HTMX, S3-compatible storage

## Goals / Non-Goals

**Goals:**
- Establecer estructura de directorios Django estándar con apps modulares bajo `apps/`
- Configurar calidad de código con Black (100), Ruff, isort, pre-commit hooks
- Crear configuración de Docker Compose para desarrollo local
- Agregar workflows básicos de GitHub Actions (CI, lint, test)
- Implementar `.gitignore` completo y `.editorconfig`
- Configurar manejo de secretos con `.env.example` y pre-commit hooks de detect-secrets
- Crear archivo `CODEOWNERS` para revisión automática

**Non-Goals:**
- No se crean los modelos ni lógica de negocio (eso será en changes futuros de CAP-001)
- No se configura producción (eso será en un change de infraestructura)
- No se integran servicios externos (SNIES, SISBÉN, OCCRE — manual/externo)
- No se implementan pipelines de deployment a producción

## Decisions

### 1. Estructura de directorios: `apps/` vs nivel raíz

**Decisión**: Usar `apps/` como directorio raíz para todas las apps Django.

**Rationale**: Mantiene la raíz limpia para archivos de configuración del proyecto. Alineado con el patrón "Django apps directory" recomendado para proyectos medianos/grandes.

**Alternativas consideradas**:
- `fodejas/apps/` — anidado, más verboso
- Sin directorio (`accounts/`, `convocatories/`) — mezcla con archivos de config

### 2. Formato de configuración: `pyproject.toml` único

**Decisión**: Usar `pyproject.toml` como fuente única de configuración para Black, Ruff, isort, pytest.

**Rationale**: Herramientas modernas coalescen en `pyproject.toml`. Reduce archivos de configuración dispersos. Compatible con `setuptools` y `hatch`.

**Alternativas consideradas**:
- Múltiples archivos (`setup.cfg`, `.flake8`, `pytest.ini`) — más archivos, menos coherente
- Solo `pyproject.toml` para Python 3.11+ — preferible pero `setup.cfg` mantiene compatibilidad con herramientas más antiguas

### 3. Pre-commit hooks

**Decisión**: Usar `pre-commit` con los siguientes hooks:
- `black` — formateo
- `ruff` — linting (reemplaza flake8, isort)
- `isort` — ordenamiento de imports
- `detect-secrets` — prevención de PII/secrets en código
- `end-of-file-fixer` — normalizar finales de línea
- `trailing-whitespace` — limpiar espacios

**Rationale**: `ruff` es 10-100x más rápido que flake8 y cubre linting + sebagian isort. `detect-secrets` previene accidental leakage de credenciales.

### 4. Docker Compose para desarrollo

**Decisión**: Crear `docker/docker-compose.yml` con servicios:
- `db` (PostgreSQL 16)
- `redis`
- `minio` (S3-compatible storage)
- `app` (Django con volúmenes)

**Rationale**: Desarrollo local idéntico a producción. MinIO evita dependencias de AWS en desarrollo.

### 5. CODEOWNERS

**Decisión**: Crear `CODEOWNERS` con propietario por defecto y secciones para:
- `/apps/accounts/` → ownership técnico
- `/openspec/` → ownership de arquitectura
- `/.github/` → DevOps ownership

**Rationale**: Garantiza revisión por personas adecuadas según el dominio del cambio.

## Risks / Trade-offs

- **[Riesgo]** Pre-commit hooks pueden causar fricción inicial → **Mitigación**: Documentar claramente y proporcionar script de setup (`scripts/setup.sh`)
- **[Riesgo]** Configuración de Docker puede divergir de producción → **Mitigación**: Usar misma imagen base, variables de entorno alineadas
- **[Riesgo]** Múltiples archivos de spec pueden perderse → **Mitigación**: Estructura OpenSpec clara, automatización de validaciones

## Migration Plan

1. Crear estructura de directorios
2. Agregar archivos de configuración base
3. Configurar pre-commit (`pip install pre-commit && pre-commit install`)
4. Verificar que los hooks funcionan: `pre-commit run --all-files`
5. Documentar setup en `CONTRIBUTING.md`

## Open Questions

- ¿Se requiere configuración específica de IDE (VS Code, PyCharm)? — Por ahora solo `.editorconfig` genérico
- ¿Se necesita scripts de setup automatizado (Makefile, bash)? — Incluir `scripts/setup.sh` básico
