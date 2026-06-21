## Why

El setup actual del proyecto (inf-001-repo-bootstrap) deja la creación del entorno virtual y la configuración de desarrollo local a responsabilidad de cada desarrollador, lo que genera fricción y configuración inconsistente. Se necesita un setup automatizado y documentado que garantice una experiencia de desarrollo local consistente y reduzca el tiempo de onboarding.

## What Changes

- Crear script `scripts/create_venv.sh` que cree y configure el entorno virtual automáticamente
- Crear script `scripts/dev.sh` que levante servicios Docker y ejecute Django con hot reload
- Crear archivo `Makefile` con comandos de desarrollo shortcuts (make dev, make test, make lint)
- Crear `.env.development` con configuración local por defecto
- Mejorar `docker/docker-compose.override.yml` para desarrollo local con volúmenes y hot reload
- Agregar configuración de Django para auto-reload y logging Development
- Crear `scripts/wait_for_services.sh` para esperar a que los servicios estén listos antes de iniciar Django
- Actualizar `CONTRIBUTING.md` con nuevos comandos de setup simplificado

## Capabilities

### New Capabilities
- `local-dev-env`: Configuración y automatización del entorno de desarrollo local incluyendo virtual environment, scripts de setup, y comandos Makefile.

### Modified Capabilities
- `repo-infrastructure`: Se extiende con scripts adicionales y configuración de desarrollo local.

## Impact

- Nuevos archivos: `scripts/create_venv.sh`, `scripts/dev.sh`, `Makefile`, `.env.development`, `scripts/wait_for_services.sh`
- Modificados: `docker/docker-compose.override.yml`, `config/settings.py`, `CONTRIBUTING.md`
- Dependencias: Docker, Docker Compose, Python 3.12+ (pre-existente)
