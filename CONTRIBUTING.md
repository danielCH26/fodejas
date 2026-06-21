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
   cp .env.development .env
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

## OpenSpec Workflow

Este proyecto usa OpenSpec para gestión de cambios. Ver `openspec/` para más detalles.

## Preguntas

Para preguntas, abrir un issue o contactar al equipo en el canal interno.
