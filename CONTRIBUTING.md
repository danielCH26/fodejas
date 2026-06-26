# Guía de Contribución

¡Gracias por tu interés en contribuir a FODEJAS!

## Requisitos Previos

- Python 3.12+
- Docker y Docker Compose
- Git

## Setup del Entorno de Desarrollo

### Setup Automatizado (Recomendado)

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd fodejas
   ```

2. **Crear entorno virtual e instalar dependencias**
   ```bash
   ./scripts/create_venv.sh
   ```

3. **Iniciar entorno de desarrollo completo**
   ```bash
   make dev
   ```
   Esto levanta los servicios Docker (PostgreSQL, Redis, MinIO) y el servidor Django con hot reload.

### Setup Manual

1. **Clonar el repositorio**
   ```bash
   git clone <repository-url>
   cd fodejas
   ```

2. **Crear y activar un entorno virtual**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # or
   .venv\Scripts\activate  # Windows
   ```

3. **Instalar dependencias**
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configurar variables de entorno para desarrollo**
   ```bash
   cp .env.development.example .env
   ```

5. **Levantar servicios con Docker**
   ```bash
   make dev.up
   # o manualmente:
   # docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml up -d
   ```

6. **Esperar a que los servicios estén listos**
   ```bash
   ./scripts/wait_for_services.sh
   ```

7. **Ejecutar migraciones y levantar servidor**
   ```bash
   python manage.py migrate
   make dev.run
   ```

## Comandos de Desarrollo

| Comando | Descripción |
|---------|-------------|
| `make dev` | Inicia entorno completo (Docker + Django) |
| `make dev.up` | Solo servicios Docker |
| `make dev.run` | Solo servidor Django |
| `make test` | Ejecutar pruebas |
| `make lint` | Validar código (ruff, black, isort) |
| `make clean` | Limpiar archivos temporales |

## Troubleshooting

### Puerto ya en uso
Si el puerto 8000 está ocupado:
```bash
lsof -i :8000
kill <PID>
```

### Servicios Docker no levantan
```bash
docker compose -f docker/docker-compose.yml logs db
docker compose -f docker/docker-compose.yml logs redis
```

### Problemas con el entorno virtual
```bash
rm -rf .venv
./scripts/create_venv.sh
```

## Workflow de Desarrollo

### Ramas

- `main` — rama de producción (solo merge via PR)
- `develop` — rama de integración
- `feat/<id>-<slug>` — nuevas funcionalidades
- `fix/<id>-<slug>` — correcciones
- `chore/<slug>` — tareas de mantenimiento

### Commits

Usamos Conventional Commits:

```
feat(CAP-001): add authentication and role management
fix(CAP-003): resolve application validation error
chore: update dependencies
```

### Pull Requests

1. Crear PR desde `feat/<id>-<slug>` → `develop`
2. Asegurar que CI pase
3. Solicitar review aowners del área afectada
4. Squash merge a develop

## Calidad de Código

El proyecto usa:

- **Black** para formateo (line-length: 100)
- **Ruff** para linting
- **isort** para orden de imports
- **detect-secrets** para prevenir secretos en código

Ejecutar validaciones localmente:

```bash
ruff check .
black --check .
isort --check .
pre-commit run --all-files
```

## Testing

```bash
pytest
```

**Nota sobre tests:** Durante la fase inicial del proyecto, los tests son opcionales.
El pipeline de CI no fallará si no existen tests. Esta restricción se removerá
automáticamente cuando el equipo comience a agregar tests al proyecto.

## CI/CD Pipeline

El proyecto usa GitHub Actions para integración continua y despliegues:

### Workflows Disponibles

| Workflow | Trigger | Descripción |
|----------|---------|-------------|
| `ci.yml` | push/PR a main o develop | Linting y tests |
| `docker-build.yml` | push a main o develop | Build y push de imagen Docker |
| `deploy-staging.yml` | manual | Despliegue a entorno staging |
| `deploy-production.yml` | manual | Despliegue a producción (requiere reviewer) |

### Imágenes Docker

- **Registry:** Docker Hub (`docker.io/danielch26/fodejas`)
- **Tags:**
  - `staging` — imagen de desarrollo/integración
  - `latest` — imagen de producción (desde main)
  - `sha-<hash>` — imagen por commit

### Environments

El proyecto usa GitHub Environments con protección:

- **staging:** Despliegue automático en merge a `develop`
- **production:** Despliegue manual via workflow dispatch, requiere 1 reviewer mínimo

### Variables de Entorno

El proyecto usa `django-environ` para configuración via variables de entorno (12-factor app).

#### Archivos .env

| Archivo | Entorno | Uso |
|---------|---------|-----|
| `.env.development.example` | development | Desarrollo local con valores por defecto |
| `.env.staging.example` | staging | Pre-producción, requiere configuración |
| `.env.production.example` | production | Producción, requiere secretos |

#### Variables comunes

```bash
# Entorno
DJANGO_ENV=development|staging|production

# Django
DEBUG=True|False
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database (PostgreSQL)
DATABASE_URL=postgres://user:password@host:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=  # opcional

# S3/MinIO
AWS_S3_ENDPOINT_URL=http://localhost:9000
```

#### Desarrollo local

El archivo `.env.development.example` contiene valores seguros para desarrollo local.
Copia y usa:

```bash
cp .env.development.example .env
```

#### Staging/Production

Los archivos `.env.staging.example` y `.env.production.example` marcan con
`# REQUIRED:` las variables que debes configurar antes de desplegar.

```bash
# Staging
cp .env.staging.example .env
# Editar y completar las variables # REQUIRED

# Production
cp .env.production.example .env
# Editar y completar las variables # REQUIRED
```

## Gestión de Secretos

El proyecto usa un servicio centralizado de gestión de secretos (`apps/core/secrets.py`) que proporciona una interfaz abstracta para recuperar secretos de cualquier almacenamiento.

### Servicio de Secretos

El módulo `apps.core.secrets` proporciona:

- `SecretStore`: Clase abstracta base
- `EnvSecretStore`: Implementación para desarrollo local (lee de variables de entorno)
- `MissingSecretError`: Excepción cuando un secreto requerido no está configurado

### Uso en Código

```python
from apps.core.secrets import secrets

# Obtener secreto opcional (retorna None si no existe)
value = secrets.get("SECRET_KEY")

# Obtener secreto requerido (lanza MissingSecretError si no existe)
value = secrets.get_required("SECRET_KEY")
```

### Detección de Secretos en Commits

El proyecto usa `detect-secrets` (pre-commit hook + CI) para prevenir que secretos sean comprometidos.

**Pre-commit hook:**
- Se ejecuta automáticamente en cada `git commit`
- Bloquea el commit si detecta un secreto no permitido
- Usa `.secrets.baseline` como lista de secretos permitidos

**CI scan:**
- El job `secrets-scan` en CI verifica que no haya secretos nuevos
- Fallará si se comprometen secretos no listados en el baseline

### Agregar un Secreto al Baseline

Si detect-secrets bloquea un commit por un "falso positivo" (ej: una cadena que parece un secreto pero no lo es), puedes agregarla al baseline:

```bash
# Usar el audit tool de detect-secrets
detect-secrets audit .secrets.baseline
```

Para permitir un secreto conocido de desarrollo:

```bash
# Marcar como "allowed" en el baseline
detect-secrets scan --baseline .secrets.baseline .
git add .secrets.baseline
git commit -m "chore: allowlist development secret"
```

### Políticas de Rotación

| Secreto | Período de Rotación | Proceso |
|---------|---------------------|---------|
| `SECRET_KEY` | 90 días | Generar nueva key, coordinar deploy |
| Credenciales DB | 180 días | Rotación DBA, actualizar Vault |
| Redis password | 90 días | Actualizar via Vault |
| AWS keys | 180 días | Rotación IAM en AWS |
| SMTP password | 30 días | Solicitar via IT |

### Troubleshooting

**Error: "Required secret 'X' is not set"**
- Verifica que la variable de entorno está configurada
- En desarrollo: copia `.env.development.example` a `.env` y completa los `# REQUIRED`
- En staging/production: configura las variables en el sistema de despliegue

**Error: "Missing required secrets for production environment"**
- Este error aparece al iniciar Django con `DJANGO_ENV=production`
- Verifica que todas las variables requeridas están configuradas:
  - `SECRET_KEY`
  - `REDIS_PASSWORD`
  - `AWS_SECRET_ACCESS_KEY`

**detect-secrets bloquea un commit válido**
- Si el "secreto" es solo un string que parece secreto (ej: `password123` en un test), puedes agregarlo al baseline
- Si es un secreto real, nunca lo commitees - usa variables de entorno o un secrets manager

**CI fails en secrets-scan**
- No hagas commit de secretos reales
- Usa el workflow de rotación para cambiar secretos comprometidos
- Si es un falso positivo, actualiza el baseline con `detect-secrets audit`

## PostgreSQL Production Setup

El proyecto usa PostgreSQL 16 con PgBouncer como connection pooler.

### Arquitectura

```
Django App → PgBouncer (port 6432) → PostgreSQL (port 5432)
```

### Configuración de Producción

| Componente | Archivo | Descripción |
|------------|---------|-------------|
| PostgreSQL tuning | `docker/postgres.conf` | Parámetros optimizados para producción |
| PgBouncer | `docker/pgbouncer.ini` | Connection pooling en modo transaction |

### Variables de Entorno para Producción

```bash
# Connection string (apunta a PgBouncer)
DATABASE_URL=postgresql://fodejas_user:fodejas_password@pgbouncer:6432/fodejas_db
```

### Backups

Los backups se ejecutan automáticamente:

| Tipo | Frecuencia | Retención | Ubicación |
|------|------------|-----------|----------|
| Base backup | Diario | 7 días | S3 (MinIO bucket `fodejas-backups`) |
| WAL archives | Continuo | 30 días | S3 (MinIO bucket `fodejas-backups`) |

**Scripts de backup:**
- `scripts/backup/base_backup.sh` — Base backup completo
- `scripts/backup/wal_archive.sh` — Archive de WAL
- `scripts/backup/backup_verify.sh` — Verificación de integridad

### Monitoreo

El dashboard de Grafana incluye métricas de PostgreSQL:
- Conexiones activas
- Cache hit ratio
- Latencia de queries
- Uso de disco

### Restauración de Backup

```bash
# 1. Descargar backup
mc cp s3://fodejas-backups/base/<backup_date>/ /tmp/restore/

# 2. Extraer
tar -xzf /tmp/restore/base.tar.gz -C /tmp/restore/

# 3. Restaurar
pg_restore -h db -U fodejas_user -d fodejas_db /tmp/restore/*.tar.gz
```

### Troubleshooting PgBouncer

**Error: "maximum connections exceeded"**
- El pool de PgBouncer está saturado
- Verificar `default_pool_size` en `pgbouncer.ini`
- Revisar queries lentas que mantienen conexiones

**Error: "connection timeout"**
- PostgreSQL no responde
- Verificar salud del servicio PostgreSQL
- Revisar logs de PostgreSQL

**Verificar estado de PgBouncer:**
```bash
# Conectar al admin interface
psql -h pgbouncer -p 6432 -U postgres -d pgbouncer
SHOW POOLS;
SHOW CLIENTS;
```

## OpenSpec Workflow

Este proyecto usa OpenSpec para gestión de cambios. Ver `openspec/` para más detalles.

## Preguntas

Para preguntas, abrir un issue o contactar al equipo en el canal interno.
