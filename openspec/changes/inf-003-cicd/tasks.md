## 1. GitHub Actions workflow files

- [ ] 1.1 Create `.github/workflows/ci.yml` for lint and tests
  - [ ] 1.1.1 Configure lint job (ruff, black, isort) — siempre obligatorio
  - [ ] 1.1.2 Configure test job con verificación de existencia de tests
  - [ ] 1.1.3 Jobs deben correr en paralelo
- [ ] 1.2 Create `.github/workflows/build-image.yml` for Docker build and push
- [ ] 1.3 Create `.github/workflows/deploy-staging.yml` for staging deployment
- [ ] 1.4 Create `.github/workflows/deploy-production.yml` for production deployment

## 2. Docker production build

- [ ] 2.1 Update `docker/Dockerfile` to multi-stage production build
- [ ] 2.2 Add production entrypoint without development dependencies
- [ ] 2.3 Test Docker build locally

## 3. Wait-for-services script

- [ ] 3.1 Create `docker/wait-for-services.sh` script
  - [ ] 3.1.1 Implementar wait para PostgreSQL usando `pg_isready`
  - [ ] 3.1.2 Implementar wait para Redis usando `redis-cli ping`
  - [ ] 3.1.3 Configurar timeout máximo (60s PostgreSQL, 30s Redis)
  - [ ] 3.1.4 Hacer script executable
- [ ] 3.2 Integrar script en Entrypoint del Dockerfile

## 4. Docker Compose con health checks

- [ ] 4.1 Create/update `docker-compose.yml`
  - [ ] 4.1.1 Configurar healthcheck para PostgreSQL
  - [ ] 4.1.2 Configurar healthcheck para Redis
  - [ ] 4.1.3 Usar `depends_on` con `condition: service_healthy`
- [ ] 4.2 Crear `docker-compose.staging.yml` overrides
- [ ] 4.3 Crear `docker-compose.production.yml` overrides

## 5. GitHub Environments configuration

- [ ] 5.1 Configure `staging` environment in GitHub
- [ ] 5.2 Configure `production` environment in GitHub with required reviewers
- [ ] 5.3 Add environment secrets:
  - [ ] `DOCKER_REGISTRY` — valor: `docker.io`
  - [ ] `DOCKER_REPOSITORY` — valor: `danielch26/fodejas`
  - [ ] `DOCKER_TOKEN_STAGING` — token Docker Hub con acceso write para staging
  - [ ] `DOCKER_TOKEN_PRODUCTION` — token Docker Hub con acceso write para production
  - [ ] `POSTGRES_PASSWORD` — password de PostgreSQL
  - [ ] `REDIS_PASSWORD` — password de Redis (si aplica)

## 6. Branch protection

- [ ] 6.1 Enable branch protection on `develop` branch
- [ ] 6.2 Enable branch protection on `main` branch
- [ ] 6.3 Require PR reviews before merge
- [ ] 6.4 Require status checks to pass before merge

## 7. Documentation

- [ ] 7.1 Add CI badges to README.md
- [ ] 7.2 Update CONTRIBUTING.md with CI/CD workflow information
  - [ ] 7.2.1 Documentar que tests son opcionales en fase inicial
  - [ ] 7.2.2 Explicar cómo agregar tests cuando se necesiten
  - [ ] 7.2.3 Documentar variables de entorno requeridas (POSTGRES_*, REDIS_*)
