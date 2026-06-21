## Why

El proyecto FODEJAS necesita integración continua y despliegue automatizado (CI/CD) para garantizar calidad de código consistente, detectar problemas tempranamente, y habilitar despliegues reproducibles a entornos de staging y producción.

Actualmente no existe pipeline de CI/CD, lo que significa que linting, tests, y despliegues se realizan manualmente, generando inconsistencias y riesgo de errores.

## What Changes

- Crear workflow de GitHub Actions para lint (ruff, black, isort)
- Crear workflow de GitHub Actions para ejecutar tests con pytest
- Crear workflow para construir y empujar imagen Docker a registry
- Crear workflow de despliegue a entorno staging
- Crear workflow de despliegue a entorno producción
- Configurar branch protection rules para `main` y `develop`
- Agregar badges de CI/CD en README.md

## Capabilities

### New Capabilities
- `ci-cd-pipeline`: Pipeline de GitHub Actions con lint, tests, build Docker, y despliegues a staging/prod

## Impact

- Nuevos archivos: `.github/workflows/ci.yml`, `.github/workflows/deploy-staging.yml`, `.github/workflows/deploy-production.yml`, `.github/workflows/build-image.yml`
- Modificados: `README.md` (badges), `docker/Dockerfile` (multi-stage build para producción)
- Dependencias: GitHub Actions (free tier), Docker registry (configurable), Python 3.12+, Django 5
