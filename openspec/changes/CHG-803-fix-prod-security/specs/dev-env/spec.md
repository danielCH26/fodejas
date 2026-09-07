# Delta — `specs/dev-env`

> Solo bloques delta (ADDED / MODIFIED). NO re-establece el spec
> existente. Origen: CHG-803 / AUD-018 (CRITICAL) y `roadmap.md`
> §4.1 INF-002.

## ADDED Requirements

### ADDED — WSGI / `gunicorn` en contenedor de producción (CAP-INF-002)

- `docker/Dockerfile` **SHALL** declarar `CMD` como
  `["gunicorn", "config.wsgi:application", "--bind",
  "0.0.0.0:8000", "--workers", "3", "--timeout", "60",
  "--access-logfile", "-", "--error-logfile", "-"]`.
- `gunicorn` **SHALL** estar declarado en
  `pyproject.toml` con `version>=21.2` para soportar
  `gunicorn config.wsgi:application` como entrypoint.
- `config/wsgi.py` **SHALL NOT** modificarse (es el entrypoint
  estándar de `django-admin startproject`).
- Tres workers **SHALL** ser el default de producción (un valor
  conservador para un solo vCPU; ajustar con `--workers` según
  capacidad del entorno). El timeout de 60s **SHALL** proteger
  contra requests colgadas que mantengan un worker ocupado
  indefinidamente.

### ADDED — Compose de producción invoca `gunicorn` (CAP-INF-002)

- `docker/docker-compose.production.yml` **SHALL** sobrescribir el
  `command` del servicio `app` con
  `command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60 --access-logfile - --error-logfile -`.
- El servicio `app` en `docker/docker-compose.production.yml`
  **SHALL NOT** invocar `python manage.py runserver`. Django
  upstream documenta `runserver` como "NOT intended for use in
  production" (Django docs §`runserver`): no tiene worker pool,
  no maneja graceful shutdown, no sirve estáticos de forma
  performante.
- `docker/docker-compose.yml` (base, dev) **SHALL** seguir
  invocando `python manage.py runserver 0.0.0.0:8000` en el
  servicio `app` para preservar el flujo de desarrollo con
  autoreload.

### ADDED — Dependencias nuevas (CAP-INF-002 / CAP-INF-010)

- `pyproject.toml` **SHALL** declarar en `[project].dependencies`:
  - `gunicorn>=21.2`
  - `django-cors-headers>=4.3`
- Estas dependencias **SHALL** instalarse via `pip install -e
  ".[dev]"` en el `Dockerfile` (stage `builder`).

### ADDED — Documentación de variables de entorno (CAP-INF-002)

- `.env.production.example` **SHALL** documentar las nuevas
  variables de entorno usadas en producción:
  - `CSRF_TRUSTED_ORIGINS=https://fodejas.gov.co,https://www.fodejas.gov.co`
  - `CORS_ALLOWED_ORIGINS=https://fodejas.gov.co,https://www.fodejas.gov.co`
  - `ALLOWED_HOSTS=fodejas.gov.co,www.fodejas.gov.co` (recordatorio;
    ya documentada, reforzar que es **obligatoria**).

## MODIFIED Requirements

### MODIFIED — Comando de arranque del contenedor `app` (CAP-INF-002)

- Antes: `docker/Dockerfile` y
  `docker/docker-compose.production.yml` corrían `python manage.py
  runserver 0.0.0.0:8000`. `docker-compose.yml` (dev) también.
- Después: `docker/Dockerfile` y
  `docker/docker-compose.production.yml` corren `gunicorn` como
  se documenta arriba. `docker/docker-compose.yml` (dev)
  mantiene `runserver` para preservar el hot-reload del flujo de
  desarrollo local.
