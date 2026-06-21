## Context

FODEJAS es una plataforma Django 5 + PostgreSQL 16 + Redis + Celery + MinIO.
Actualmente no tiene pipeline de CI/CD, lo que significa que linting, tests, y despliegues
se realizan manualmente. Se necesita automatizar el ciclo de desarrollo para garantizar
calidad consistente y despliegues reproducibles.

## Goals / Non-Goals

**Goals:**
- Automatizar lint (ruff, black, isort) en cada PR y push
- Automatizar tests con pytest en cada PR y push
- Construir imagen Docker multi-stage para producción
- Desplegar a staging automáticamente en merge a `develop`
- Desplegar a producción manualmente via workflow dispatch
- Proteger ramas `main` y `develop` con PR requirements

**Non-Goals:**
- No se implementa deploy automático a producción (solo manual via workflow dispatch)
- No se integra con sistemas externos (SNIES, SISBÉN, bancos)
- No se crea infraestructura como código (IaC) para AWS u otro cloud
- No se implementa rollback automático

## Decisions

### 1. Workflow único CI vs múltiples workflows

**Decisión:** Usar un workflow `ci.yml` que combina lint y tests.

**Alternativas consideradas:**
- Workflows separados para lint y tests — más granular pero más archivos
- Workflows combinados — menor overhead, suficiente para el proyecto

**Elección:** Workflow único `ci.yml` que corre lint y tests en paralelo.

**Justificación:** Reduce archivos YAML, los jobs son independientes así que pueden correr
en paralelo, y la estructura es simple de mantener.

### 2. Docker build strategy

**Decisión:** Multi-stage build con Dockerfile optimizado para producción.

**Alternativas consideradas:**
- Build en local y push — requiere credenciales en máquina del dev
- Build en GitHub Actions — centralizado, auditado, reproducible

**Elección:** GitHub Actions construye y empuja la imagen.

**Justificación:** No hay credenciales en máquinas de desarrollo, el build es reproducible,
y se puede usar cache de Docker layer para speed.

### 3. Registry Docker

**Decisión:** Usar GitHub Container Registry (ghcr.io).

**Alternativas consideradas:**
- Docker Hub — requiere credenciales management
- AWS ECR — integración con AWS pero más complejo
- Google GCR — similar a ECR

**Elección:** ghcr.io con formato `ghcr.io/<owner>/<image>:tag`.

**Justificación:** Integrado con GitHub, gratuito para repos públicos (500MB storage free),
no requiere credenciales externas.

### 4. Branch strategy para deployments

**Decisión:** Staging en merge a `develop`, Producción via manual dispatch.

**Alternativas consideradas:**
- Todos los deploys manuales — mayor control pero más fricción
- Deploy automático a producción en merge a main — riesgo de cambios no probados

**Elección:** Staging automático, producción manual.

**Justificación:** Staging automático permite testers/devs verificar antes de producción.
Producción manual permite control fino del momento de deploy.

### 5. Environment strategy

**Decisión:** Usar GitHub Environments con protection rules.

**Alternativas consideradas:**
- Variables de entorno en workflow — menos granular
- Secrets a nivel de repo — suficiente pero sin protection rules

**Elección:** GitHub Environments (`staging`, `production`) con reviewers requirement.

**Justificación:** Environment protection rules permiten required reviewers antes de
deploy a producción. Los secrets son per-environment.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Credenciales Docker expuestas | Usar OIDC federation con GitHub Actions, no static credentials |
| Deploy a producción falla | Workflow dispatch permite seleccionar tag específico |
| Workflows muy largos | Jobs paralelos, cache de pip y docker layers |
| Rate limits de GitHub Actions | Plan gratuito tiene 2000 min/mes, suficiente para este proyecto |

## Migration Plan

1. Crear workflows en `.github/workflows/`
2. Agregar Dockerfiles para producción (multi-stage)
3. Configurar GitHub Environments con protection rules
4. Probar workflow en branch feature
5. Merge a `develop` — deploy automático a staging
6. Hacer PR de `develop` a `main`
7. Verificar staging, luego manually trigger production deploy

## Open Questions

1. ¿Cuántos reviewers se requieren para deploy a producción?
   - **Decision:** 1 reviewer mínimo (configurable en environment)
2. ¿Se usa caching para Docker build?
   - **Decision:** Sí, usar `docker/setup-buildx-action` y cache-to/cache-from
3. ¿Tags de Docker image?
   - **Decision:** `latest`, `staging`, y tag con commit SHA (e.g., `sha-abc1234`)
