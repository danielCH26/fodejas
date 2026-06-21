# Guía de Contribución

¡Gracias por tu interés en contribuir a FODEJAS!

## Requisitos Previos

- Python 3.12+
- Docker y Docker Compose
- Git

## Setup del Entorno de Desarrollo

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

4. **Configurar variables de entorno**
   ```bash
   cp .env.example .env
   # Editar .env con la configuración local
   ```

5. **Instalar pre-commit hooks**
   ```bash
   ./scripts/setup.sh
   ```

6. **Levantar servicios con Docker**
   ```bash
   docker compose -f docker/docker-compose.yml up -d
   ```

7. **Ejecutar migraciones**
   ```bash
   python manage.py migrate
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
