# Runbook de Despliegue — FODEJAS

> Procedimiento manual paso a paso. Los workflows GitHub Actions
> `deploy-staging.yml` y `deploy-production.yml` son **placeholders**;
> no automatizan nada todavía.
>
> Referencia: roadmap.md INF-012.

## Prerrequisitos

- Acceso al registry Docker (`docker.io/danielch26/fodejas`).
- Acceso SSH al servidor de staging o producción.
- Variables de entorno configuradas en el servidor (ver §Variables).
- Permisos de superusuario en la base de datos staging/producción.

---

## 1. Construcción de imagen Docker (opcional si ya existe)

Si el workflow `docker-build.yml` ya construyó la imagen en GitHub Actions,
omitir esta sección y usar el tag generado automáticamente:

- Rama `develop` → tag `staging`
- Rama `main` → tag `latest`
- Tags específicos → `sha-<hash>` (recomendado para producción)

### Construcción manual

```bash
# Desde la raíz del repositorio
docker build \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  -f docker/Dockerfile \
  -t danielch26/fodejas:<tag> \
  .

# Verificar que la imagen se creó
docker images danielch26/fodejas
```

El `docker/Dockerfile` por defecto ejecuta Gunicorn (comando CMD).
El `docker-compose.yml` base lo sobreescribe con `runserver` (desarrollo).

---

## 2. Variables de entorno requeridas

Todas las variables se alimentan al contenedor vía `environment` en el
`docker-compose.staging.yml` / `docker-compose.production.yml` o un archivo
`.env` importado por el compose.

| Variable | Fuente segura | Desarrollo por defecto | Descripción |
|---|---|---|---|
| `DATABASE_URL` | Secrets server | `postgres://fodejas_user:fodejas_password@pgbouncer:6432/fodejas_db` | Conexión BD (staging/prod pasa por PgBouncer) |
| `REDIS_URL` | Secrets server | `redis://redis:6379/0` | URL de Redis |
| `REDIS_PASSWORD` | `apps.core.secrets` (prod/staging) | vacío | Contraseña de Redis para producción |
| `SECRET_KEY` | `apps.core.secrets` (prod/staging) | `django-insecure-dev-only...` | Clave Django (nunca en producción por defecto) |
| `DEBUG` | — | `True` dev / `False` staging+prod | **False obligatorio en producción** |
| `DJANGO_ENV` | — | `development` | `staging` o `production` |
| `ALLOWED_HOSTS` | Secrets server | `localhost,127.0.0.1` | Hosts válidos (producción: dominio real) |
| `AWS_ACCESS_KEY_ID` | Secrets server | `minioadmin` | Clave MinIO/S3 |
| `AWS_SECRET_ACCESS_KEY` | `apps.core.secrets` (prod/staging) | `minioadmin` | Secreto MinIO/S3 |
| `AWS_STORAGE_BUCKET_NAME` | — | `fodejas-media` | Bucket de medios |
| `AWS_S3_ENDPOINT_URL` | — | `http://localhost:9000` | Endpoint MinIO (producción: URL real) |
| `MINIO_ENDPOINT` | — | `minio:9000` | Endpoint MinIO interno |
| `MINIO_ACCESS_KEY` | Secrets server | `minioadmin` | Usuario MinIO |
| `MINIO_SECRET_KEY` | `apps.core.secrets` (prod/staging) | `minioadmin` | Contraseña MinIO |
| `SENTRY_DSN` | Secrets server (opcional) | vacío | DSN Sentry (si se usa) |
| `SIGNATURE_PROVIDER` | — | `mock` | `mock` (dev), `local` (staging+prod) — **nunca `mock` en producción** |
| `ELECTRONIC_SIGNATURE_PROVIDER` | — | `mock` | Alias de `SIGNATURE_PROVIDER` |

> **Fuente de secretos:** `apps/core/secrets.py` implementa `EnvSecretStore`,
> que lee de variables de entorno. En producción los valores sensibles se
> injectan vía secrets del servidor (no hardcodear en el repo).

### Validación de producción

```bash
# Verificar que DEBUG=False y DJANGO_ENV=production antes de desplegar
docker compose exec app env | grep -E "DEBUG|DJANGO_ENV|SIGNATURE_PROVIDER"
```

---

## 3. Secuencia de despliegue (staging y producción)

### 3.1 pull o build de la imagen

```bash
# Pull desde registry (si ya existe)
docker pull danielch26/fodejas:<tag>

# O construir localmente (ver §1)
```

### 3.2 Actualizar compose con la nueva imagen

Editar `docker-compose.production.yml` o `docker-compose.staging.yml`
y cambiar el `image:` del servicio `app` al tag deseado:

```yaml
services:
  app:
    image: danielch26/fodejas:<tag>   # ej: sha-abc1234
```

### 3.3 Levantar/actualizar los servicios

```bash
# Producción (desde el directorio docker/)
cd /path/al/servidor/docker
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d app

# Staging
docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d app
```

### 3.4 Entrypoint automático

El `entrypoint.sh` ejecuta automáticamente en cada inicio del contenedor:

```bash
# 1. Espera que db y redis estén disponibles (wait-for-services.sh)
# 2. python manage.py migrate --noinput          ← migraciones
# 3. python manage.py collectstatic --noinput   ← archivos estáticos
```

**No es necesario ejecutar migrate manualmente** salvo que se quiera
verificar antes de levantar el contenedor.

### 3.5 Orden de seeds (primera vez o tras migrate)

Ejecutar **después** de que las migraciones terminen, en este orden:

```bash
# 1. Migraciones (automático en entrypoint)
docker compose exec app python manage.py migrate --noinput

# 2. Crear roles base (si no existen)
docker compose exec app python manage.py seed_roles

# 3. Sincronizar permisos de grupos con capacidades (CAP-001)
docker compose exec app python manage.py sync_roles

# 4. Verificar configuración de firma electrónica
#    IMPORTANTE: falla con exit 1 si SIGNATURE_PROVIDER=mock en staging/producción
docker compose exec app python manage.py check_signer_config

# 5. Solo en desarrollo: crear usuarios de prueba
#    NO ejecutar en staging ni producción
docker compose exec app python manage.py create_test_users
```

> **CHG-506 (rama `feat/CHG-506-impact-study`):**
> Los comandos `seed_municipio_isla` y `backfill_impact_fields`
> **no existen en esta rama** (`feat/CHG-507-multilang`).
> Una vez que `feat/CHG-506-impact-study` se mergee a `develop`,
> ejecutar estos comandos tras `sync_roles`:
>
> ```bash
> docker compose exec app python manage.py seed_municipio_isla
> docker compose exec app python manage.py backfill_impact_fields
> ```
>
> Documentar la ejecución en el changelog de infraestructura.

### 3.6 Verificación post-despliegue

```bash
# a) Liveness: siempre debe responder 200
curl -f http://localhost:8000/healthz
# Esperado: {"status": "ok"}

# b) Readiness: DB + Redis checks (5s timeout, 503 si falla algo)
curl -f http://localhost:8000/readyz
# Esperado (todo ok):  {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}
# Esperado (falló):    503 + {"status": "unhealthy", "checks": {...}}

# c) Métricas Prometheus accesibles
curl -sf http://localhost:8000/metrics | head -5

# d) Login funcional: abrir http://localhost:8000/admin/
#    Verificar que la página carga y el formulario de login responde.

# e) Consola MinIO: verificar que el bucket fodejas-media existe
mc ls local/fodejas-media

# f) Verificar Celery Beat: contar tareas registradas
docker compose exec celery-beat celery -A config inspect scheduled | \
  python -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d)} tareas beat registradas')"
```

---

## 4. Rollback

### 4.1 Rollback de imagen Docker

```bash
# Identificar la imagen anterior por tag o commit SHA
docker images danielch26/fodejas

# Usar tag sha-<commit_anterior> en lugar del actual
# Editar image: en docker-compose.production.yml y re-levantar:
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d app
```

### 4.2 Consideración sobre migraciones

**Las migraciones de Django son forward-only.** Si el nuevo código incluye
migraciones nuevas y se hace rollback de imagen:

1. La imagen anterior puede no conocer las tablas/columnas nuevas.
2. **No ejecutar `migrate` hacia atrás (`python manage.py migrate <app> <previous>`).**
3. El rollback de código con migraciones nuevas requiere evaluación
   caso por caso por el líder técnico.
4. Si la migración fue destructiva (DROP COLUMN, DROP TABLE), **no es reversible
   sin restaurar desde backup**.

**Si se detecta que una migración impidió el rollback:**
- Restaurar la imagen anterior **no revertirá** la migración.
- La única opción es restaurar la base de datos desde backup
  (ver [`02-backup-disaster-recovery.md`](02-backup-disaster-recovery.md)).

---

## 5. Compilación de traducciones

Los archivos `.mo` están commiteados en el repo (`locale/*/LC_MESSAGES/django.mo`).

Solo se requiere recompilar si se editan archivos `.po`:

```bash
# Requiere polib (ya instalado en el contenedor)
python scripts/compile_mo.py

# Resultado esperado:
#   OK  [es       ] django.po -> django.mo  (N translated)
#   OK  [en       ] django.po -> django.mo  (N translated)
# Compiled 2/2 locale(s).
```

---

## 6. Tareas programadas de Celery (beat)

El schedule Celery Beat (zona horaria `America/Bogota`) es:

| Tarea | Schedule | Propósito |
|---|---|---|
| `tesoreria-sweep-v5d` | 09:00 L-V | Barrido de tesorería (vencimiento 5 días) |
| `tesoreria-alert-v5d` | 08:00 L-V | Alerta previa de tesorería |
| `exoneracion-sweep-v30d` | 09:05 daily | Barrido de exoneraciones (30 días) |
| `exoneracion-alert-v30d` | 09:10 daily | Alerta previa de exoneraciones |
| `habeas-sweep-v30d` | 09:15 daily | Barrido Habeas Data (30 días) |
| `habeas-alert-v30d` | 09:20 daily | Alerta previa Habeas Data |

Todas las tareas son **idempotentes**: ejecutan `last_alerted_at` + sentinel
en la tabla de auditoría para no duplicar alertas en el mismo día.

Si Redis cae → Beat se detiene silenciosamente → las tareas no se ejecutan.
`readyz` reporta Redis como fallido y devuelve 503.

---

## 7. Despliegue de Celery Worker y Beat

```bash
# Worker (producción)
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d celery-worker

# Beat (producción)
docker compose -f docker-compose.yml -f docker-compose.production.yml up -d celery-beat
```

**Orden de arranque:** db → redis → app → pgbouncer → minio → celery-worker → celery-beat.

---

## 8. Checklist pre-despliegue

- [ ] `DEBUG=False` y `DJANGO_ENV=staging|production` en el compose.
- [ ] `SIGNATURE_PROVIDER=local` (nunca `mock` en staging/producción).
- [ ] `SECRET_KEY`, `REDIS_PASSWORD`, `AWS_SECRET_ACCESS_KEY` inyectados desde secrets.
- [ ] Base de datos accesible (`pg_isready`).
- [ ] Imagen construida o pull exitosa.
- [ ] Ejecutar seed order si es primera vez o hay migraciones nuevas.
- [ ] Verificar `/readyz` → 200 OK.
- [ ] Verificar login en `/admin/`.
- [ ] Notificar al equipo de que el deploy completó.

---

Anterior: [`README.md`](README.md)
|
Siguiente: [`02-backup-disaster-recovery.md`](02-backup-disaster-recovery.md)
