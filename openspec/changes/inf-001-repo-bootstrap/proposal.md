# Bootstrap del Repositorio FODEJAS

## Why

El proyecto FODEJAS necesita una base sólida de configuración de proyecto que garantice calidad de código consistente, seguridad en el manejo de secretos, documentación uniformada y colaboración efectiva entre equipos. Sin estas configuraciones iniciales, el proyecto carece de higiene básica de desarrollo.

## What Changes

- Crear estructura de directorios estándar Django con apps modulares (`apps/accounts/`, `apps/convocatories/`, `apps/applications/`, etc.)
- Configurar `.gitignore` completo para Python/Django/Docker/VirtualEnv/IDE
- Agregar `.editorconfig` para consistencia entre editores
- Configurar pre-commit hooks con Black, Ruff, isort, detect-secrets y otros linters
- Crear archivo `CODEOWNERS` para revisión automática de código
- Agregar archivos base de configuración: `pyproject.toml`, `setup.cfg`, `.env.example`
- Crear estructura de directorios OpenSpec (`openspec/specs/`, `openspec/changes/`)
- Agregar archivos base para Docker Compose y GitHub Actions

## Capabilities

### New Capabilities

- `repo-infrastructure`: Infraestructura inicial del repositorio incluyendo estructura de directorios, configuración de calidad de código, hooks de git, y archivos base del proyecto.

### Modified Capabilities

_(Ninguna — este change es puramente infraestructura)_

## Impact

- Nueva estructura de directorios en la raíz del proyecto
- Archivos de configuración agregados en la raíz
- Pre-commit hooks activos en `.git/hooks/`
- GitHub Actions workflows básicos en `.github/workflows/`
- Docker configuration en `docker/`
