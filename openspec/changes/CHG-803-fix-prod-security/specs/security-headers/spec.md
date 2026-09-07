# Delta — `specs/security-headers`

> Solo bloques delta (ADDED / MODIFIED). NO re-establece el spec
> existente. Origen: CHG-803 / AUD-017 (CRITICAL), AUD-021 (WARNING)
> y `roadmap.md` §4.2 Anexo "Security Headers".

## ADDED Requirements

### ADDED — Cabeceras de seguridad en producción (CAP-INF-010)

- `config/settings.py` **SHALL** declarar, dentro de un bloque
  `if IS_PRODUCTION:` (definido por la constante `IS_PRODUCTION =
  DJANGO_ENV in ("staging", "production")`), todas las cabeceras
  de seguridad listadas en el Anexo "Security Headers" del
  `roadmap.md` §4.2. Concretamente:
  - `SECURE_SSL_REDIRECT = True`
  - `SECURE_HSTS_SECONDS = 31_536_000` (1 año)
  - `SECURE_HSTS_INCLUDE_SUBDOMAINS = True`
  - `SECURE_HSTS_PRELOAD = True`
  - `SECURE_CONTENT_TYPE_NOSNIFF = True`
  - `SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"`
  - `SESSION_COOKIE_SECURE = True`
  - `CSRF_COOKIE_SECURE = True`
  - `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`
  - `CSRF_TRUSTED_ORIGINS = ["https://fodejas.gov.co",
    "https://www.fodejas.gov.co"]`
  - `X_FRAME_OPTIONS = "DENY"`
- La política HSTS con `preload` se aplica **únicamente** al dominio
  de producción confirmado (`fodejas.gov.co`). Staging puede omitir
  `SECURE_HSTS_PRELOAD` para evitar cualificar el subdominio de
  staging para el preload list de navegadores; la rama `if
  IS_PRODUCTION:` no distingue staging de producción, por lo que el
  equipo de operaciones **SHALL** reversar `SECURE_HSTS_PRELOAD` en
  staging hasta que se decida el dominio final.
- `X_FRAME_OPTIONS = "DENY"` **SHALL** declararse explícitamente
  (no heredar el default `"SAMEORIGIN"` de
  `XFrameOptionsMiddleware`).

### ADDED — `ALLOWED_HOSTS` estricto en producción (CAP-INF-010)

- En producción, `ALLOWED_HOSTS` **SHALL** leerse de la variable de
  entorno `ALLOWED_HOSTS` (lista separada por comas). Si la
  variable está vacía o no está definida, `ALLOWED_HOSTS` **SHALL**
  ser la lista vacía — Django rechazará todas las requests con
  `400 Bad Request — Invalid HTTP_HOST` y eso **SHALL** fallar
  rápido en el arranque del contenedor.
- En desarrollo (`DJANGO_ENV=development`), el default **SHALL**
  seguir siendo `["localhost", "127.0.0.1", "0.0.0.0", "*"]` para
  no romper el flujo con `runserver` local.
- El default en producción **SHALL NOT** contener `*` ni
  `0.0.0.0` (riesgo de host header injection, OWASP A07:2021).

### ADDED — Límites de upload (CAP-003 FUI anexos)

- `config/settings.py` **SHALL** declarar, **globalmente** (no solo
  en producción), `DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024`
  y `FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024` (10 MB cada
  uno).
- Django **SHALL** rechazar con `400 Bad Request` y excepción
  `RequestDataTooBig` cualquier request cuyo body exceda
  `DATA_UPLOAD_MAX_MEMORY_SIZE`. Para uploads multipart, el límite
  combinado de `FILE_UPLOAD_MAX_MEMORY_SIZE` +
  `DATA_UPLOAD_MAX_MEMORY_SIZE` aplica; el body completo no puede
  exceder 10 MB.
- Los anexos del FUI (PDFs de cédula, diplomas) típicamente pesan
  entre 2 MB y 8 MB; el límite de 10 MB **SHALL** dejar margen sin
  permitir adjuntos arbitrariamente grandes que faciliten DoS por
  request.
- El default de Django (2.5 MB) **SHALL NOT** aplicarse, porque
  excluye anexos legítimos.

### ADDED — CORS (CAP-INF-010)

- `corsheaders` **SHALL** estar en `INSTALLED_APPS`.
- `corsheaders.middleware.CorsMiddleware` **SHALL** aparecer en
  `MIDDLEWARE` inmediatamente después de
  `django.middleware.security.SecurityMiddleware` (CorsMiddleware
  debe correr antes de `CommonMiddleware` para que los headers
  `Access-Control-*` se agreguen antes de la respuesta).
- En producción, `CORS_ALLOWED_ORIGINS` **SHALL** ser una lista
  explícita con los orígenes oficiales:
  `["https://fodejas.gov.co", "https://www.fodejas.gov.co"]`.
- En producción, `CORS_ALLOW_CREDENTIALS` **SHALL** ser `True`
  (cookies de sesión deben poder enviarse en requests
  cross-origin autenticados).
- `CORS_ALLOW_ALL_ORIGINS` **SHALL NOT** ser `True` (no se
  permite CORS abierto; el default del paquete es `False`).
- En desarrollo, `CORS_ALLOWED_ORIGINS` no necesita estar
  definido (no hay orígenes remotos en dev); el middleware queda
  inerte.

## MODIFIED Requirements

### MODIFIED — HTTPS obligatorio en todos los entornos no-locales (roadmap §4.2)

- Antes: `SECURE_SSL_REDIRECT` no estaba declarado y la auditoría
  detectó que HTTPS no se forzaba programáticamente.
- Después: `SECURE_SSL_REDIRECT = True` bajo `if IS_PRODUCTION:`
  en `config/settings.py`. Toda request HTTP entrante al
  contenedor `app` en staging/prod **SHALL** ser redirigida a
  HTTPS vía el header `Location: https://...` retornado por
  `SecurityMiddleware`.
