# Tasks — Bootstrap del Repositorio FODEJAS

## 1. Proyecto Django base

- [ ] 1.1 Crear proyecto Django con `django-admin startproject config .` en la raíz
- [ ] 1.2 Mover `config/` a la estructura deseada y ajustar paths en manage.py
- [ ] 1.3 Crear directorio `apps/` en la raíz del proyecto
- [ ] 1.4 Crear estructura base para `apps/accounts/` (models.py, views.py, urls.py, admin.py, apps.py, __init__.py)
- [ ] 1.5 Crear estructura base para `apps/convocatories/`
- [ ] 1.6 Crear estructura base para `apps/applications/`
- [ ] 1.7 Crear estructura base para `apps/scoring/`
- [ ] 1.8 Crear estructura base para `apps/claims/`
- [ ] 1.9 Crear estructura base para `apps/legalization/`
- [ ] 1.10 Crear estructura base para `apps/treasury/`
- [ ] 1.11 Crear estructura base para `apps/academic_tracking/`
- [ ] 1.12 Crear estructura base para `apps/psychosocial/`
- [ ] 1.13 Crear estructura base para `apps/condonation/`
- [ ] 1.14 Crear estructura base para `apps/governance/`
- [ ] 1.15 Crear estructura base para `apps/reporting/`
- [ ] 1.16 Crear estructura base para `apps/audit/`
- [ ] 1.17 Crear estructura base para `apps/core/` (models.py, admin.py, apps.py)

## 2. Archivos de configuración del proyecto

- [ ] 2.1 Crear `pyproject.toml` con configuración de Black, Ruff, isort, pytest
- [ ] 2.2 Crear `.env.example` con todas las variables de entorno requeridas (DEBUG, SECRET_KEY, DATABASE_URL, REDIS_URL, etc.)
- [ ] 2.3 Crear `.gitignore` completo para Python, Django, Docker, IDE, VirtualEnv, __pycache__, .env
- [ ] 2.4 Crear `.editorconfig` con configuración para Python, YAML, JSON, Markdown

## 3. Pre-commit hooks

- [ ] 3.1 Crear `.pre-commit-config.yaml` con hooks de black, ruff, isort, detect-secrets, end-of-file-fixer, trailing-whitespace
- [ ] 3.2 Crear `.secrets.baseline` para detect-secrets
- [ ] 3.3 Crear script `scripts/setup.sh` que instale pre-commit y configure hooks

## 4. Docker Compose

- [ ] 4.1 Crear directorio `docker/`
- [ ] 4.2 Crear `docker/Dockerfile` con Python 3.12 y dependencias del proyecto
- [ ] 4.3 Crear `docker/docker-compose.yml` con servicios: db (PostgreSQL 16), redis, minio
- [ ] 4.4 Crear `docker/docker-compose.override.yml` para desarrollo local con hot-reload
- [ ] 4.5 Crear `docker/entrypoint.sh` para inicialización del contenedor Django

## 5. GitHub Actions

- [ ] 5.1 Crear `.github/workflows/ci.yml` con jobs: lint, test
- [ ] 5.2 Crear `.github/workflows/code-quality.yml` con Black, Ruff, isort en modo check
- [ ] 5.3 Crear `.github/workflows/docker-build.yml` para construcción de imagen

## 6. CODEOWNERS y documentación

- [ ] 6.1 Crear `CODEOWNERS` con secciones para openspec/, apps/, .github/
- [ ] 6.2 Crear `CONTRIBUTING.md` con guía de contribución y setup
- [ ] 6.3 Crear `README.md` con información del proyecto y badges

## 7. Validación

- [ ] 7.1 Verificar que `pre-commit install` funciona correctamente
- [ ] 7.2 Verificar que `docker compose up -d` levanta todos los servicios
- [ ] 7.3 Verificar que `pytest` corre sin errores (aunque no haya tests aún)
- [ ] 7.4 Verificar que `ruff check .` pasa sin errores
- [ ] 7.5 Verificar que `black --check .` pasa sin errores
