## Why

El proyecto FODEJAS necesita integración continua y despliegue automatizado (CI/CD) para garantizar calidad de código consistente, detectar problemas tempranamente, y habilitar despliegues reproducibles a entornos de staging y producción.

Actualmente no existe pipeline de CI/CD, lo que significa que linting, tests, y despliegues se realizan manualmente, generando inconsistencias y riesgo de errores.

## What Changes

- Crear workflow de GitHub Actions para lint (ruff, black, isort)
- Crear workflow de GitHub Actions para ejecutar tests con pytest
- Crear workflow para construir y empujar imagen Docker a Docker Hub
- Crear workflow de despliegue a entorno staging
- Crear workflow de despliegue a entorno producción
- Usar Docker tokens como secrets para autenticación a Docker Hub
- Configurar branch protection rules para `main` y `develop`
- Agregar badges de CI/CD en README.md
- Pipeline no fallará cuando no existan tests (fase inicial del proyecto)
- Crear script de espera (`wait-for-services.sh`) para PostgreSQL y Redis
- Configurar health checks en docker-compose para validar disponibilidad de servicios

## Capabilities

### New Capabilities
- `ci-cd-pipeline`: Pipeline de GitHub Actions con lint, tests, build Docker, y despliegues a staging/prod

## Impact

- Nuevos archivos:
  - `.github/workflows/ci.yml` — lint y tests
  - `.github/workflows/deploy-staging.yml` — deploy a staging
  - `.github/workflows/deploy-production.yml` — deploy a producción
  - `.github/workflows/build-image.yml` — build y push de imagen Docker
  - `docker/wait-for-services.sh` — script de espera para PostgreSQL y Redis
  - `docker-compose.yml` — configuración con health checks
- Modificados: `README.md` (badges), `docker/Dockerfile` (multi-stage build para producción)
- Dependencias: GitHub Actions (free tier), Docker Hub (`danielch26/fodejas`), Python 3.12+, Django 5, PostgreSQL 16, Redis
- Secrets requeridos:
  - `DOCKER_TOKEN_STAGING`, `DOCKER_TOKEN_PRODUCTION` — tokens Docker Hub
  - `DOCKER_REGISTRY`, `DOCKER_REPOSITORY` — configuración del registry
  - `POSTGRES_PASSWORD`, `REDIS_PASSWORD` — passwords de servicios (en environments)
- Nota: El job de tests es opcional en fase inicial; linting siempre es obligatorio
