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
- Soportar despliegues con PostgreSQL y Redis como servicios externos

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

**Justificación:** No hay credenciales en máquinas de desarrolladores, el build es reproducible,
y se puede usar cache de Docker layer para speed.

### 3. Registry Docker

**Decisión:** Usar Docker Hub con el repositorio existente `danielch26/fodejas`.

**Alternativas consideradas:**
- GitHub Container Registry (ghcr.io) — integrado con GitHub pero diferente al repositorio existente
- AWS ECR — más complejo y requiere credenciales cloud
- Google GCR — similar a ECR

**Elección:** Docker Hub `docker.io/danielch26/fodejas`.

**Justificación:** Repositorio ya existe con tokens disponibles para staging y production,
familiaridad del equipo con Docker Hub, tokens permiten autenticación directa.

### 4. Autenticación al Registry

**Decisión:** Usar Docker tokens de Docker Hub almacenados como GitHub Environment Secrets.

**Alternativas consideradas:**
- OIDC federation — más seguro pero requiere configuración adicional de cloud provider
- SSH deploy keys — no aplica para registry Docker
- Username/password directo — menos granular que tokens

**Elección:** Docker tokens como environment secrets.

**Justificación:** Simple de implementar, tokens específicos por environment (staging/production),
fácil de rotar, y compatible con Docker Hub.

### 5. Branch strategy para deployments

**Decisión:** Staging en merge a `develop`, Producción via manual dispatch.

**Alternativas consideradas:**
- Todos los deploys manuales — mayor control pero más fricción
- Deploy automático a producción en merge a main — riesgo de cambios no probados

**Elección:** Staging automático, producción manual.

**Justificación:** Staging automático permite testers/devs verificar antes de producción.
Producción manual permite control fino del momento de deploy.

### 6. Environment strategy

**Decisión:** Usar GitHub Environments con protection rules.

**Alternativas consideradas:**
- Variables de entorno en workflow — menos granular
- Secrets a nivel de repo — suficiente pero sin protection rules

**Elección:** GitHub Environments (`staging`, `production`) con reviewers requirement.

**Justificación:** Environment protection rules permiten required reviewers antes de
deploy a producción. Los secrets son per-environment.

### 7. Tests opcionales en fase inicial

**Decisión:** El job de tests en el pipeline NO fallará cuando no existan tests.

**Alternativas consideradas:**
- Fallar si no hay tests — bloquea el pipeline prematuramente en fase inicial
- Requerir archivo de configuración para deshabilitar tests — overhead innecesario
- Tests obligatorios desde el inicio — ideal pero inviable en fase inicial

**Elección:** Usar `--ignore=tests` o verificar existencia de tests antes de ejecutar.

**Justificación:** El proyecto está en fase inicial y aún no existen tests. El pipeline
debe pasar sin errores para permitir que el equipo progrese. Linting siempre es obligatorio;
tests se agregan cuando el código lo requiera. Una vez existan tests, se移除 la excepción.

**Implementación sugerida en `ci.yml`:**
```yaml
- name: Run tests
  run: |
    if [ -d "tests" ] || find . -name "test_*.py" -o -name "*_test.py" | grep -q .; then
      pytest --tb=short
    else
      echo "No tests found, skipping..."
    fi
```

### 8. Espera de servicios externos (PostgreSQL y Redis)

**Decisión:** Usar scripts de health check con retry para esperar que PostgreSQL y Redis
estén disponibles antes de iniciar la aplicación Django.

**Alternativas consideradas:**
- Usar `depends_on` de Docker Compose — solo espera a que el contenedor inicie, no a que el servicio esté listo
- Hardcoded sleep — ineficiente, no garantiza que el servicio esté realmente disponible
- No esperar — la aplicación falla si los servicios no están listos

**Elección:** Scripts de wait con verificación de conexión y reintentos.

**Justificación:** PostgreSQL y Redis pueden tardar en estar listos incluso después de que
el contenedor haya iniciado. La aplicación necesita verificar la disponibilidad real antes
de intentar conexiones. Se usa un enfoque simple con `pg_isready` para PostgreSQL y
verificación de conexión Redis.

**Variables de entorno requeridas:**
```bash
POSTGRES_HOST= # hostname del servicio PostgreSQL
POSTGRES_PORT=5432
POSTGRES_DB= # nombre de la base de datos
POSTGRES_USER= # usuario
POSTGRES_PASSWORD= # password (via secret)

REDIS_HOST= # hostname del servicio Redis
REDIS_PORT=6379
REDIS_PASSWORD= # password (via secret, opcional)
```

**Script sugerido `docker/wait-for-services.sh`:**
```bash
#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  echo "PostgreSQL unavailable, retrying..."
  sleep 2
done
echo "PostgreSQL is ready!"

echo "Waiting for Redis..."
until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ${REDIS_PASSWORD:+-a "$REDIS_PASSWORD"} ping > /dev/null 2>&1; do
  echo "Redis unavailable, retrying..."
  sleep 2
done
echo "Redis is ready!"

exec "$@"
```

**Configuración de health checks en `docker-compose.yml` (staging/prod):**
```yaml
services:
  app:
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
  postgres:
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 10
  redis:
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 10
```

**Timeout máximo:** 60 segundos para PostgreSQL, 30 segundos para Redis.
Si se excede, el contenedor falla con mensaje de error claro.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| Credenciales Docker expuestas | Usar Docker tokens como environment secrets con rotación periódica |
| Tokens expiran sin alerta | Establecer recordatorio para rotación antes de expiración (máx 1 año) |
| Deploy a producción falla | Workflow dispatch permite seleccionar tag específico |
| Workflows muy largos | Jobs paralelos, cache de pip y docker layers |
| Rate limits de GitHub Actions | Plan gratuito tiene 2000 min/mes, suficiente para este proyecto |
| Tests nunca se agregan | Agregar como checklist en onboarding y recordatorios trimestrales |
| PostgreSQL no está listo | Health check con retry hasta 60s antes de fallar |
| Redis no está listo | Health check con retry hasta 30s antes de fallar |

## Migration Plan

1. Crear workflows en `.github/workflows/`
2. Actualizar `docker/Dockerfile` para producción (multi-stage)
3. Crear script `docker/wait-for-services.sh` para health checks
4. Crear/actualizar `docker-compose.yml` con health checks para PostgreSQL y Redis
5. Configurar GitHub Environments con protection rules y secrets de tokens
6. Probar workflow en branch feature
7. Merge a `develop` — deploy automático a staging
8. Hacer PR de `develop` a `main`
9. Verificar staging, luego manually trigger production deploy

## Open Questions

1. ¿Cuántos reviewers se requieren para deploy a producción?
   - **Decision:** 1 reviewer mínimo (configurable en environment)
2. ¿Se usa caching para Docker build?
   - **Decision:** Sí, usar `docker/setup-buildx-action` y cache-to/cache-from
3. ¿Tags de Docker image?
   - **Decision:** `latest`, `staging`, y tag con commit SHA (e.g., `sha-abc1234`)
4. ¿Rotación de tokens?
   - **Decision:** Tokens Docker Hub tienen expiración máxima de 1 año;
     establecer recordatorio a los 11 meses para rotar
5. ¿Timeouts de health check?
   - **Decision:** PostgreSQL: 60s máximo, Redis: 30s máximo, interval de 5s
