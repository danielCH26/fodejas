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

## OpenSpec Workflow

Este proyecto usa OpenSpec para gestión de cambios. Ver `openspec/` para más detalles.

## Preguntas

Para preguntas, abrir un issue o contactar al equipo en el canal interno.
