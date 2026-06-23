## 1. GitHub Actions workflow files

- [x] 1.1 Create `.github/workflows/ci.yml` for lint and tests
  - [x] 1.1.1 Configure lint job (ruff, black, isort) — siempre obligatorio
  - [x] 1.1.2 Configure test job con verificación de existencia de tests
  - [x] 1.1.3 Jobs deben correr secuencialmente (lint → test)
- [x] 1.2 Create `.github/workflows/build-image.yml` for Docker build and push
- [x] 1.3 Create `.github/workflows/deploy-staging.yml` for staging deployment
- [x] 1.4 Create `.github/workflows/deploy-production.yml` for production deployment

## 2. Docker production build

- [x] 2.1 Update `docker/Dockerfile` to multi-stage production build
- [x] 2.2 Add production entrypoint without development dependencies
- [x] 2.3 Test Docker build locally (verified via CI/CD pipeline)

## 3. Wait-for-services script

- [x] 3.1 Create `docker/wait-for-services.sh` script
  - [x] 3.1.1 Implementar wait para PostgreSQL usando `pg_isready`
  - [x] 3.1.2 Implementar wait para Redis usando `redis-cli ping`
  - [x] 3.1.3 Configurar timeout máximo (60s PostgreSQL, 30s Redis)
  - [x] 3.1.4 Hacer script executable
- [x] 3.2 Integrar script en Entrypoint del Dockerfile

## 4. Docker Compose con health checks

- [x] 4.1 Create/update `docker-compose.yml`
  - [x] 4.1.1 Configurar healthcheck para PostgreSQL
  - [x] 4.1.2 Configurar healthcheck para Redis
  - [x] 4.1.3 Usar `depends_on` con `condition: service_healthy`
- [x] 4.2 Crear `docker-compose.staging.yml` overrides
- [x] 4.3 Crear `docker-compose.production.yml` overrides

## 5. GitHub Environments configuration

- [x] 5.1 Configure `staging` environment in GitHub
- [x] 5.2 Configure `production` environment in GitHub with required reviewers
- [x] 5.3 Add environment secrets:
  - [x] `DOCKER_REGISTRY` — valor: `docker.io`
  - [x] `DOCKER_REPOSITORY` — valor: `danielch26/fodejas`
  - [x] `DOCKER_TOKEN_STAGING` — token Docker Hub con acceso write para staging
  - [x] `DOCKER_TOKEN_PRODUCTION` — token Docker Hub con acceso write para production
  - [x] `POSTGRES_PASSWORD` — password de PostgreSQL
  - [x] `REDIS_PASSWORD` — password de Redis (si aplica)

## 6. Branch protection

- [x] 6.1 Enable branch protection on `develop` branch
- [x] 6.2 Enable branch protection on `main` branch
- [x] 6.3 Require PR reviews before merge
- [x] 6.4 Require status checks to pass before merge

## 7. Documentation

- [x] 7.1 Add CI badges to README.md
- [x] 7.2 Update CONTRIBUTING.md with CI/CD workflow information
  - [x] 7.2.1 Documentar que tests son opcionales en fase inicial
  - [x] 7.2.2 Explicar cómo agregar tests cuando se necesiten
  - [x] 7.2.3 Documentar variables de entorno requeridas (POSTGRES_*, REDIS_*)
