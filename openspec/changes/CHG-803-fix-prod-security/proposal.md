# CHG-803 — Cabeceras de seguridad + WSGI de producción + límites de upload

## Contexto

La auditoría completa del 2026-09-05 (`docs/audits/extended-audit.md`
AUD-017, AUD-018, AUD-021) detectó tres defectos graves en la
configuración de producción:

1. **AUD-017 CRITICAL**: `config/settings.py` no declara ninguna
   cabecera de seguridad de producción. Faltan `SECURE_SSL_REDIRECT`,
   `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`,
   `SECURE_HSTS_PRELOAD`, `SECURE_CONTENT_TYPE_NOSNIFF`,
   `SECURE_REFERRER_POLICY`, `SESSION_COOKIE_SECURE`,
   `CSRF_COOKIE_SECURE`, `SECURE_PROXY_SSL_HEADER`,
   `CSRF_TRUSTED_ORIGINS`. `roadmap.md:213-215` requiere explícitamente
   "HTTPS obligatorio en todos los entornos no-locales" y "headers de
   seguridad activos en staging y prod".
2. **AUD-018 CRITICAL**: `docker/docker-compose.production.yml:16` y
   `docker/Dockerfile:39` corren `python manage.py runserver
   0.0.0.0:8000`. Django upstream documenta `runserver` como "NOT
   intended for use in production" - sin worker pool, sin graceful
   shutdown, sin handler de estáticos.
3. **AUD-021 WARNING**: `DATA_UPLOAD_MAX_MEMORY_SIZE` y
   `FILE_UPLOAD_MAX_MEMORY_SIZE` no están configurados. El default de
   Django es 2.5 MB; los anexos del FUI (PDFs de cédulas, diplomas)
   típicamente exceden eso.

## Capacidades afectadas

- **INF-010** (Security headers, `roadmap.md:166`).
- **INF-002** (Local dev env + producción via Docker).
- **CAP-003** (FUI digital con anexos — afectado por upload limits).

## Reglas de negocio afectadas

- `AGENTS.md` §6 regla 1 (no exponer datos en tránsito sin TLS).
- `roadmap.md` §4.2 Entregables (HTTPS obligatorio + rate limiting +
  headers de seguridad).
- `roadmap.md` §4.3 Criterio de salida (plataforma desplegable y
  observable en staging y prod).

## Cambios propuestos

### Delta en `specs/security-headers/spec.md`

#### ADDED — § Cabeceras de seguridad en producción

`config/settings.py` **SHALL** declarar bajo un bloque
`if IS_PRODUCTION:` todas las cabeceras del Anexo "Security Headers"
del roadmap §4.2. Concretamente:

```python
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
CSRF_TRUSTED_ORIGINS = ["https://fodejas.gov.co",
                         "https://www.fodejas.gov.co"]
X_FRAME_OPTIONS = "DENY"
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10 MB
```

`ALLOWED_HOSTS` en producción **SHALL** ser explícito (sin `*`, sin
`0.0.0.0`). El default dev puede seguir siendo permisivo.

### Delta en `specs/dev-env/spec.md`

#### MODIFIED — § Comando de arranque en contenedor

`docker/Dockerfile` **SHALL** declarar `CMD` como `gunicorn` para
imagen base; `docker/docker-compose.yml` puede sobreescribirlo por
servicio. `docker/docker-compose.production.yml` **SHALL** invocar
`gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
--timeout 60 --access-logfile - --error-logfile -`.

#### ADDED — § CORS

`CORS_ALLOWED_ORIGINS` **SHALL** declararse en
`config/settings.py` bajo `if IS_PRODUCTION:` con los orígenes
oficiales. `CORS_ALLOW_ALL_ORIGINS = False`.

### Cambios concretos

1. `config/settings.py`:
   - Bloque `if IS_PRODUCTION:` con todas las cabeceras listadas.
   - `DATA_UPLOAD_MAX_MEMORY_SIZE` y `FILE_UPLOAD_MAX_MEMORY_SIZE`
     globales (10 MB).
   - `CORS_ALLOWED_ORIGINS` y `CORS_ALLOW_CREDENTIALS = True` en
     producción.
   - `ALLOWED_HOSTS` por defecto `[]` para `IS_PRODUCTION`,
     explícito via env en `.env.production.example`.
2. `pyproject.toml` — agregar `gunicorn>=21.0` y `django-cors-headers`.
3. `docker/Dockerfile:39` — `CMD ["gunicorn", "config.wsgi:application",
   "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60"]`.
4. `docker/docker-compose.production.yml:16` — cambiar a
   `command: gunicorn config.wsgi:application --bind 0.0.0.0:8000
   --workers 3 --timeout 60 --access-logfile - --error-logfile -`.
5. `docker/docker-compose.yml` — agregar servicio
   `web-dev: ... command: python manage.py runserver 0.0.0.0:8000`
   (mantiene dev) y mantener prod override.
6. `.env.production.example` — documentar
   `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`,
   `ALLOWED_HOSTS`.
7. `config/urls.py` — agregar `CorsMiddleware` (de
   `django-cors-headers`) en `MIDDLEWARE` justo después de
   `SecurityMiddleware`.

## Criterios de aceptación

- [ ] En staging, `curl -I https://staging.fodejas.gov.co/` devuelve
      `Strict-Transport-Security`, `X-Content-Type-Options`,
      `X-Frame-Options: DENY`, `Referrer-Policy`.
- [ ] En staging, una cookie de sesión tiene el flag `Secure`.
- [ ] `docker compose -f docker/docker-compose.production.yml
      config` muestra `command: gunicorn ...` en el servicio web.
- [ ] `curl -X POST -F "file=@big.pdf" https://staging/api/...`
      con PDF de 8 MB responde 201; con PDF de 12 MB responde 400
      con `RequestDataTooBig`.
- [ ] `pytest --ds=config.settings` carga sin errores con
      `DJANGO_ENV=production`.
- [ ] `manage.py check --deploy` no reporta issues de seguridad.

## Pruebas

- Unitarias:
  - `config/tests/test_settings_prod.py` — verifica que las claves
    SECURE_* están definidas bajo `DJANGO_ENV=production`.
  - `config/tests/test_upload_limits.py` — requests con body de
    11 MB devuelven 400.
- Integración:
  - `tests/security/test_headers.sh` — script que hace `curl -I`
    contra staging y verifica la presencia de cada cabecera.
- Performance:
  - Smoke test post-deploy: gunicorn arranca en <5s, responde
    `/healthz` en <50ms.

## Riesgos y Fuera del alcance

- **Riesgo**: HSTS preload es una decisión irreversible para el
  dominio. Solo aplicar en dominio de producción confirmado
  (`fodejas.gov.co`). Staging puede tener HSTS sin preload.
- **Riesgo**: subir el límite de upload a 10 MB aumenta la
  superficie de ataque DoS por request grande. Mitigación: rate
  limiting (queda en otro change — CHG-INF-010-rate-limit) y
  nginx con `client_max_body_size 10m`.
- **Fuera del alcance**:
  - No se migra la base de datos de Postgres ni se cambia
    PgBouncer.
  - No se agrega CDN / WAF (queda para Fase 0 INF-010-ext).
  - Rate limiting detallado (queda para change separado).

## Referencias

- `docs/audits/extended-audit.md` §3, §8.2 AUD-017, AUD-018,
  §8.3 AUD-021.
- `roadmap.md` §4.1 INF-010, §4.2 Entregables.
- `AGENTS.md` §6 regla 1.
