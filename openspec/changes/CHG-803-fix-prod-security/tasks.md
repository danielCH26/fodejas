# Tasks — CHG-803 — Cabeceras de seguridad + WSGI de producción + límites de upload

> Origen: `proposal.md` (AUD-017 CRITICAL, AUD-018 CRITICAL, AUD-021
> WARNING). Toda propuesta pasa por `proposal.md` + `tasks.md` + delta
> en `specs/` (AGENTS.md §4).

## 1. Cabeceras de seguridad en `config/settings.py`

- [ ] En `config/settings.py`, agregar un bloque `if IS_PRODUCTION:`
      (junto al de secretos, base de datos, logging) con todas las
      cabeceras del Anexo "Security Headers" del roadmap §4.2:
      `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`,
      `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`,
      `SECURE_CONTENT_TYPE_NOSNIFF`, `SECURE_REFERRER_POLICY`,
      `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
      `SECURE_PROXY_SSL_HEADER`, `CSRF_TRUSTED_ORIGINS`,
      `X_FRAME_OPTIONS`.
- [ ] `X_FRAME_OPTIONS = "DENY"` (no `"SAMEORIGIN"`). El header lo
      setea `XFrameOptionsMiddleware` que ya está en `MIDDLEWARE`
      (línea 122 actual).
- [ ] `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
      para honrar el proxy reverso (nginx) que termina TLS.
- [ ] `CSRF_TRUSTED_ORIGINS` con la lista oficial
      `["https://fodejas.gov.co", "https://www.fodejas.gov.co"]`.

## 2. `ALLOWED_HOSTS` estricto en producción

- [ ] Confirmar que la línea actual de `ALLOWED_HOSTS` (con default
      `["localhost","127.0.0.1","0.0.0.0","*"]` en dev y `[]` en
      prod) ya cumple la regla "explicito en prod, permisivo en dev".
      Si `ALLOWED_HOSTS` está vacío en prod, el guard `ALLOWED_HOSTS`
      se levanta: documentar en `.env.production.example` que el
      `ALLOWED_HOSTS` env var es **obligatorio** en staging/prod.
- [ ] NO usar `*` ni `0.0.0.0` en `ALLOWED_HOSTS` para producción.

## 3. Límites de upload

- [ ] Agregar `DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024` (10 MB)
      a `config/settings.py` (global, no dentro de `if IS_PRODUCTION:`)
      — aplica a body no-multipart.
- [ ] Agregar `FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024` (10 MB)
      (global) — aplica a multipart / FUI anexos.

## 4. CORS

- [ ] Agregar `"corsheaders"` a `INSTALLED_APPS`.
- [ ] Agregar `"corsheaders.middleware.CorsMiddleware"` a `MIDDLEWARE`
      justo después de `"django.middleware.security.SecurityMiddleware"`
      (CorsMiddleware debe correr antes de CommonMiddleware).
- [ ] Bajo `if IS_PRODUCTION:` en `config/settings.py`, agregar
      `CORS_ALLOWED_ORIGINS = ["https://fodejas.gov.co",
      "https://www.fodejas.gov.co"]` y
      `CORS_ALLOW_CREDENTIALS = True`.
- [ ] `CORS_ALLOW_ALL_ORIGINS = False` (default del paquete; no hace
      falta declararlo explícitamente, pero se documenta en el spec).

## 5. WSGI / `gunicorn` en contenedor

- [ ] Cambiar la línea `CMD ["runserver", "0.0.0.0:8000"]` en
      `docker/Dockerfile` por
      `CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]`.
- [ ] Cambiar la línea
      `command: python manage.py runserver 0.0.0.0:8000` en
      `docker/docker-compose.production.yml` (línea 16) por
      `command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60 --access-logfile - --error-logfile -`.
- [ ] Mantener `docker/docker-compose.yml` (servicio `app` línea 7)
      con `command: python manage.py runserver 0.0.0.0:8000` para
      dev. Agregar comentario en la cabecera del archivo recordando
      que la override de producción cambia el comando a `gunicorn`.
- [ ] `config/wsgi.py` no requiere cambios (es el entrypoint
      estándar de `startproject`).

## 6. Dependencias en `pyproject.toml`

- [ ] Agregar `gunicorn>=21.2` a `[project].dependencies`.
- [ ] Agregar `django-cors-headers>=4.3` a `[project].dependencies`.

## 7. Documentación en `.env.production.example`

- [ ] Agregar bloque comentado al final del archivo documentando
      las nuevas variables:
      `CSRF_TRUSTED_ORIGINS`,
      `CORS_ALLOWED_ORIGINS`,
      `ALLOWED_HOSTS` (recordatorio: ya está documentado arriba,
      reforzar que es obligatorio).
- [ ] Documentar `SECURE_PROXY_SSL_HEADER` si aplica (es
      constante, no se lee de env, pero documentar que nginx debe
      mandar `X-Forwarded-Proto: https`).

## 8. Tests

- [ ] `config/tests/__init__.py` (paquete vacío).
- [ ] `config/tests/test_settings_prod.py` — usa `subprocess.run` para
      levantar un Python con `DJANGO_ENV=production` y
      `ALLOWED_HOSTS=fodejas.gov.co,www.fodejas.gov.co`; verifica
      que `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`,
      `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS`
      toman los valores del Anexo. Verifica también que con
      `DJANGO_ENV=development` esas claves no rompen el import.
- [ ] `config/tests/test_upload_limits.py` — pytest con
      `DATA_UPLOAD_MAX_MEMORY_SIZE = 10 MB`; el cliente de Django
      POST-ea un body de 11 MB y espera 400
      (`RequestDataTooBig`).
- [ ] Validar el YAML de `docker/docker-compose.production.yml` con
      `python -c "import yaml; yaml.safe_load(open('docker/docker-compose.production.yml'))"`
      — no requiere Docker instalado.

## 9. Pruebas

- [ ] Unitarias: `config/tests/test_settings_prod.py`,
      `config/tests/test_upload_limits.py`.
- [ ] Integración: comando
      `python -c "import os; os.environ['DJANGO_ENV']='production'; os.environ['SECRET_KEY']='test'; os.environ['DATABASE_URL']='sqlite:///test.db'; import django; django.setup(); from django.conf import settings; print(settings.SECURE_SSL_REDIRECT, settings.SECURE_HSTS_SECONDS, settings.DATA_UPLOAD_MAX_MEMORY_SIZE)"`
      imprime `True 31536000 10485760`.
- [ ] `python manage.py check --deploy` no reporta issues nuevos de
      seguridad.
- [ ] Regresión: `pytest config/tests/ -x --no-header -q` corre
      limpio.
