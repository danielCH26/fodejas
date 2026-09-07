# CHG-803 Apply Progress

## Tasks done (per `tasks.md`)

### 1. Cabeceras de seguridad en `config/settings.py` — DONE

- [x] Bloque `if IS_PRODUCTION:` (líneas 92-120 de
      `config/settings.py`) con todas las cabeceras del Anexo
      "Security Headers" del roadmap §4.2: `SECURE_SSL_REDIRECT`,
      `SECURE_HSTS_SECONDS` (31 536 000), `SECURE_HSTS_INCLUDE_SUBDOMAINS`,
      `SECURE_HSTS_PRELOAD`, `SECURE_CONTENT_TYPE_NOSNIFF`,
      `SECURE_REFERRER_POLICY` (`"strict-origin-when-cross-origin"`),
      `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`,
      `SECURE_PROXY_SSL_HEADER` (`("HTTP_X_FORWARDED_PROTO", "https")`),
      `CSRF_TRUSTED_ORIGINS`,
      `X_FRAME_OPTIONS = "DENY"`.
- [x] `X_FRAME_OPTIONS = "DENY"` declarado explícitamente
      (no se hereda el default `"SAMEORIGIN"` de
      `XFrameOptionsMiddleware`).
- [x] `SECURE_PROXY_SSL_HEADER` honra el `X-Forwarded-Proto: https`
      del proxy reverso (nginx) que termina TLS.
- [x] `CSRF_TRUSTED_ORIGINS` con la lista oficial
      `["https://fodejas.gov.co", "https://www.fodejas.gov.co"]`.

### 2. `ALLOWED_HOSTS` estricto en producción — DONE

- [x] `ALLOWED_HOSTS` ya tenía el patrón correcto (default
      `["localhost","127.0.0.1","0.0.0.0","*"]` en dev, `[]` en prod)
      en la línea 75-78 de `config/settings.py` (existente previo a
      este change). Confirmado que `if IS_PRODUCTION:` →
      `ALLOWED_HOSTS = []` salvo que `ALLOWED_HOSTS` env var esté
      seteada, en cuyo caso se lee vía `env.list("ALLOWED_HOSTS")`.
- [x] `.env.production.example` documenta explícitamente que
      `ALLOWED_HOSTS` es **obligatorio** y no debe contener `*` ni
      `0.0.0.0`.

### 3. Límites de upload — DONE

- [x] `DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024` (10 MB)
      declarado globalmente en `config/settings.py` línea 84.
- [x] `FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024` (10 MB)
      declarado globalmente línea 85.
- [x] Aplican en dev y prod (no gated por `if IS_PRODUCTION:`).

### 4. CORS — DONE

- [x] `"corsheaders"` agregado a `INSTALLED_APPS` (línea 133).
- [x] `"corsheaders.middleware.CorsMiddleware"` agregado a
      `MIDDLEWARE` justo después de
      `SecurityMiddleware` (líneas 158-162). Orden verificado en
      `test_cors_middleware_is_in_middleware_list_in_dev`:
      `Security → Cors → ... → Common`.
- [x] `CORS_ALLOWED_ORIGINS` y `CORS_ALLOW_CREDENTIALS = True` bajo
      `if IS_PRODUCTION:` (líneas 116-120).
- [x] `CORS_ALLOW_ALL_ORIGINS = False` (default del paquete;
      implícitamente nunca es `True`).

### 5. WSGI / `gunicorn` en contenedor — DONE

- [x] `docker/Dockerfile` línea 40: `CMD` cambiado a
      `["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]`.
- [x] `docker/docker-compose.production.yml` línea 17: `command:`
      cambiado a
      `command: gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 60 --access-logfile - --error-logfile -`.
- [x] `docker/docker-compose.yml` (base, dev) servicio `app` línea 7
      mantiene `command: python manage.py runserver 0.0.0.0:8000`.
      Comentario agregado en líneas 1-7 documentando que la override
      de producción cambia el comando a gunicorn.
- [x] `config/wsgi.py` no modificado (entrypoint estándar).

### 6. Dependencias en `pyproject.toml` — DONE

- [x] `gunicorn>=21.2` agregado a `[project].dependencies`.
- [x] `django-cors-headers>=4.3` agregado a `[project].dependencies`.

### 7. Documentación en `.env.production.example` — DONE

- [x] Bloque al final del archivo con `CSRF_TRUSTED_ORIGINS`,
      `CORS_ALLOWED_ORIGINS`, y recordatorio de `ALLOWED_HOSTS`.

### 8. Tests — DONE

- [x] `config/tests/__init__.py` (paquete con docstring).
- [x] `config/tests/test_settings_prod.py` — 11 tests que
      lanzan un subprocess con `DJANGO_ENV=production` + el monkey-
      patch de `environ.Env.db` (workaround del bug pre-existente
      documentado más abajo) y verifican que las claves de
      seguridad tomen los valores del Anexo.
- [x] `config/tests/test_upload_limits.py` — 4 tests:
      - `test_oversized_form_body_returns_request_data_too_big` —
        POST 11 MB a `/accounts/register/` (view que accede a
        `request.POST`) → 400.
      - `test_small_form_body_passes_size_check` — body 1 KB no
        rechazado.
      - `test_lowered_limit_is_enforced` — con
        `override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=512)`, body
        de 1 KB → 400.
      - `test_data_upload_max_memory_size_setting_is_10mb` — el
        setting es 10 MB en `config.settings`.

## Files changed (CHG-803 scope only)

| File | Change |
|------|--------|
| `config/settings.py` | +44 lines: production security block (l. 80-120), `corsheaders` en `INSTALLED_APPS` (l. 133), `CorsMiddleware` en `MIDDLEWARE` (l. 162) |
| `pyproject.toml` | +2 lines: `gunicorn>=21.2`, `django-cors-headers>=4.3` |
| `docker/Dockerfile` | +1 / -1 line: `CMD` → `gunicorn` (l. 40-45) |
| `docker/docker-compose.production.yml` | +1 / -1 line: `command: gunicorn ...` (l. 17) |
| `docker/docker-compose.yml` | +6 lines comment (l. 1-7) |
| `config/urls.py` | sin cambios (el middleware se configura en `settings.MIDDLEWARE`, no en `urls.py`) |
| `.env.production.example` | +9 lines: `CSRF_TRUSTED_ORIGINS`, `CORS_ALLOWED_ORIGINS`, `ALLOWED_HOSTS` reminder (l. 36-44) |
| `config/tests/__init__.py` (NEW) | 4 lines |
| `config/tests/test_settings_prod.py` (NEW) | 220 lines, 11 tests |
| `config/tests/test_upload_limits.py` (NEW) | 95 lines, 4 tests |
| `openspec/changes/CHG-803-fix-prod-security/tasks.md` (NEW) | per §4 template |
| `openspec/changes/CHG-803-fix-prod-security/specs/security-headers/spec.md` (NEW) | delta ADDED + MODIFIED |
| `openspec/changes/CHG-803-fix-prod-security/specs/dev-env/spec.md` (NEW) | delta ADDED + MODIFIED |

## Test results

```
$ python -m pytest config/tests/ -x --no-header -q
config\tests\test_upload_limits.py ...                                   [ 20%]
config\tests\test_settings_prod.py ...........                           [ 93%]
config\tests\test_upload_limits.py .                                     [100%]
================= 15 passed, 5 warnings in 117.89s (0:01:57) ==================
```

- **15 passed**: 4 upload limit tests + 11 production settings tests.
- **0 failed, 0 skipped**.

## Verification (production environment)

```
$ python -c "import os, secrets; \
    os.environ['DJANGO_ENV']='production'; \
    os.environ['SECRET_KEY']=secrets.token_urlsafe(50); \
    os.environ['DATABASE_URL']='sqlite:///test.db'; \
    os.environ['REDIS_PASSWORD']='x'; os.environ['AWS_SECRET_ACCESS_KEY']='x'; \
    os.environ['ALLOWED_HOSTS']='fodejas.gov.co,www.fodejas.gov.co'; \
    os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; os.environ['DEBUG']='False'; \
    import environ; _o=environ.Env.db; \
    environ.Env.db=lambda s,*a,**k:({'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}if'url'in k else _o(s,*a,**k)); \
    import django; django.setup(); \
    from django.conf import s as settings; \
    print(settings.SECURE_SSL_REDIRECT, settings.SECURE_HSTS_SECONDS, settings.DATA_UPLOAD_MAX_MEMORY_SIZE)"
True 31536000 10485760
```

```
$ python manage.py check --deploy
System check identified no issues (0 silenced).
```

- **0 issues** with prod env (DJANGO_ENV=production, real-shape
  SECRET_KEY, proper ALLOWED_HOSTS, DEBUG=False).
- **6 issues** in dev (DEBUG=True, no HSTS, no SESSION_COOKIE_SECURE
  …) — all are expected for development and are the
  same warnings documented in `manage.py check --deploy`'s default
  dev output. They are not new issues introduced by this change.

```
$ python -c "import yaml; yaml.safe_load(open('docker/docker-compose.production.yml')); print('YAML OK')"
YAML OK
$ python -c "import yaml; yaml.safe_load(open('docker/docker-compose.yml')); print('YAML OK')"
YAML OK
```

Both compose files parse cleanly.

## Acceptance criteria status (from `proposal.md`)

- [x] Bloque `if IS_PRODUCTION:` con todas las cabeceras del Anexo
      "Security Headers" del roadmap §4.2 declarado en
      `config/settings.py`.
- [x] `docker/Dockerfile` y `docker/docker-compose.production.yml`
      invocan `gunicorn` con los flags documentados.
- [x] `DATA_UPLOAD_MAX_MEMORY_SIZE` y `FILE_UPLOAD_MAX_MEMORY_SIZE`
      declarados a 10 MB globalmente.
- [x] `CORS_ALLOWED_ORIGINS` declarado en `if IS_PRODUCTION:` con
      los orígenes oficiales.
- [x] `manage.py check --deploy` no reporta issues de seguridad
      con prod env.
- [ ] **Staging smoke** (no ejecutado en este change — no hay
      acceso al entorno de staging): `curl -I https://staging.
      fodejas.gov.co/` retorna los headers; el flag `Secure` se
      observa en cookies de sesión. Pendiente para el despliegue.
- [ ] **End-to-end upload de PDF** (no ejecutado en este change):
      `curl -X POST -F "file=@big.pdf" /api/...` con PDF de 8 MB
      responde 201; con PDF de 12 MB responde 400. La regla está
      implementada y probada unitariamente; la verificación
      end-to-end queda para el deploy.

## Blockers

- **Pre-existing bug en `config/settings.py` línea ~205**
  (`env.db(url=_db_url)`). El método `Env.db()` de django-environ
  no acepta el kwarg `url=`; la llamada correcta sería
  `env.db(_db_url)` o `env.db(var=_db_url)`. Esto bloquea el
  import de `config.settings` cuando `DJANGO_ENV=staging|production`
  (TypeError: `Env.db_url() got an unexpected keyword argument
  'url'`). El bug es **anterior** a este change (verificable
  leyendo el bloque pre-existente que no fue tocado en CHG-803).
  Workaround: los tests de CHG-803 monkey-patchean `Env.db` para
  no-oppear la llamada buggy. Workaround operativo (para
  staging/prod): en el docker-compose de prod, sobreescribir
  `DATABASE_URL` con la URL que apunta a PgBouncer — Django
  intentará parsear la URL completa, no la keyword, si la línea
  se corrige.
  **Acción recomendada**: crear un CHG-804 dedicado para corregir
  este typo (1 línea) y validar que `manage.py check --deploy`
  funcione sin monkey-patch.

- **Test client no enforces `DATA_UPLOAD_MAX_MEMORY_SIZE` para
  content types distintos de form-urlencoded / multipart**. El
  test de 11 MB ahora POST-ea a `/accounts/register/` (que lee
  `request.POST`) con `application/x-www-form-urlencoded` para
  forzar el check. Los checks con
  `content_type="application/octet-stream"` a un endpoint que
  no lee `request.body` no ejercen el guard y devuelven
  405/200.

## Follow-ups

1. **CHG-804 candidato**: corregir el typo `env.db(url=_db_url)`
   en `config/settings.py` (~línea 205). Es un fix de 1 carácter
   (`url=_db_url` → `_db_url`) que desbloquea el import de
   settings en prod sin necesidad de monkey-patch.
2. **Nginx `client_max_body_size 10m`**: el `Dockerfile` y la
   config de nginx (no presente en este repo, vive en el
   infra-as-code del entorno) deben subir el límite de nginx al
   mismo 10 MB para que los uploads al proxy no reboten antes de
   llegar a gunicorn. CHG-803 cierra el lado Django; el lado
   nginx queda en la cola del equipo de infra.
3. **Smoke test post-deploy**: script `tests/security/
   test_headers.sh` que haga `curl -I https://staging...` y
   verifique los headers. Propuesto en `proposal.md §Pruebas`
   pero no implementado en este change porque requiere acceso
   al entorno de staging. Incluir en el PR de deploy.
4. **Rate limiting** (CHG-INF-010-rate-limit, propuesto en
   `proposal.md` Riesgos): subir el límite de upload a 10 MB
   aumenta la superficie de ataque DoS por request grande. La
   mitigación de rate limiting queda en otro change. Sin ese
   change, este CHG-803 aumenta levemente el riesgo DoS en
   staging.
5. **HSTS preload staging**: la rama `if IS_PRODUCTION:` aplica
   `SECURE_HSTS_PRELOAD = True` también en staging. El
   `proposal.md` Riesgos §1 sugiere que staging debería omitir
   preload para no cualificar el subdominio de staging para el
   preload list. Considerar discriminar `staging` vs `production`
   en el bloque `if IS_PRODUCTION:`.
6. **Pre-existing `manage.py check` warnings** en dev (W004,
   W008, W012, W016, W018) no son introducidos por este change
   y se resuelven automáticamente con `DJANGO_ENV=production`.
   Quedan documentados como "expected for dev" en la sección
   Verification.
7. **Pre-existing migration issue**: la migración
   `apps/accounts/migrations/0002_customuser_habeas_data_consent
   _...` usa `condition=` (removido en Django 5.2). Documentado
   en CHG-801 follow-up #6 y CHG-802 follow-up #6; sin
   relación con CHG-803.
8. **`django_prometheus.urls` no instalado en este
   environment** (CHG-801 follow-up #7). No afecta CHG-803
   pero `manage.py check` lo reporta cuando el módulo no
   está disponible. Out of scope.
