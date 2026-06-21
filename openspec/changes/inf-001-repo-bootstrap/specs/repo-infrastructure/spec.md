# repo-infrastructure — Infraestructura del Repositorio

> Especificación delta para la capacidad de infraestructura del repositorio.
> Define los archivos, configuraciones y estructura que constituyen la base del proyecto.

## ADDED Requirements

### Requirement: Estructura de directorios Django

El proyecto SHALL mantener una estructura de directorios que separe las apps Django del código de configuración del proyecto.

#### Scenario: Directorio apps/ contiene todas las apps
- **WHEN** se crea una nueva funcionalidad del dominio
- **THEN** SHALL existir una app bajo `apps/<nombre>/` con la estructura estándar de Django (models.py, views.py, urls.py, etc.)

#### Scenario: Configuración del proyecto en raíz
- **WHEN** se busca configuración del proyecto (settings, wsgi, asgi)
- **THEN** SHALL existir en la raíz del proyecto (no dentro de apps/)

### Requirement: Control de calidad de código

El proyecto SHALL incluir configuración de herramientas de calidad de código que se ejecuten automáticamente.

#### Scenario: Black formatea código
- **WHEN** se ejecuta `black --check .` en el proyecto
- **THEN** SHALL el código cumplir con las reglas de formateo de Black con line-length=100

#### Scenario: Ruff valida código
- **WHEN** se ejecuta `ruff check .` en el proyecto
- **THEN** SHALL el código pasar todas las reglas de lint habilitadas sin errores

#### Scenario: isort ordena imports
- **WHEN** se ejecuta `isort --check .` en el proyecto
- **THEN** SHALL todos los imports estar ordenados alfabéticamente y separados por secciones (stdlib, third-party, local)

### Requirement: Pre-commit hooks

El proyecto SHALL incluir configuración de pre-commit que ejecute validaciones antes de cada commit.

#### Scenario: detect-secrets previene secretos
- **WHEN** un desarrollador intenta hacer commit de un archivo que contiene疑似 secretos (API keys, passwords, tokens)
- **THEN** SHALL el hook `detect-secrets` rechazar el commit y mostrar advertencia

#### Scenario: Black formatea antes de commit
- **WHEN** un desarrollador ejecuta `git commit`
- **THEN** SHALL el hook de pre-commit formatear automáticamente los archivos Python modificados

### Requirement: Archivos de configuración del proyecto

El proyecto SHALL incluir archivos de configuración estándar que documenten las herramientas usadas.

#### Scenario: pyproject.toml configura herramientas
- **WHEN** se abre el proyecto en un editor compatible
- **THEN** SHALL existir `pyproject.toml` con configuración de Black, Ruff, isort, pytest

#### Scenario: .env.example documenta variables
- **WHEN** un nuevo desarrollador configura el entorno local
- **THEN** SHALL existir `.env.example` con todas las variables de entorno requeridas (sin valores reales)

### Requirement: GitHub Actions CI

El proyecto SHALL incluir workflows de GitHub Actions que validen el código en cada push.

#### Scenario: CI ejecuta tests
- **WHEN** se hace push a cualquier rama
- **THEN** SHALL GitHub Actions ejecutar `pytest` y reportar resultados

#### Scenario: CI valida linting
- **WHEN** se hace push a cualquier rama
- **THEN** SHALL GitHub Actions ejecutar Black, Ruff, isort en modo check

### Requirement: Docker Compose para desarrollo

El proyecto SHALL incluir configuración Docker para levantar servicios localmente.

#### Scenario: PostgreSQL disponible localmente
- **WHEN** se ejecuta `docker compose up -d db`
- **THEN** SHALL existir un contenedor PostgreSQL 16 accesible en el puerto configurado

#### Scenario: Redis disponible localmente
- **WHEN** se ejecuta `docker compose up -d redis`
- **THEN** SHALL existir un contenedor Redis accesible en el puerto configurado

#### Scenario: MinIO disponible para storage
- **WHEN** se ejecuta `docker compose up -d minio`
- **THEN** SHALL existir un contenedor MinIO con API S3-compatible accesible en la consola web

### Requirement: CODEOWNERS para revisión

El proyecto SHALL incluir archivo CODEOWNERS que asigne propietarios a las diferentes áreas del código.

#### Scenario: Openspec tiene ownership de arquitectura
- **WHEN** se crea un PR que modifica archivos en `openspec/`
- **THEN** SHALL el equipo de arquitectura ser solicitado como reviewer

#### Scenario: Apps tiene ownership técnico
- **WHEN** se crea un PR que modifica archivos en `apps/`
- **THEN** SHALL el equipo técnico ser solicitado como reviewer
