## ADDED Requirements

### Requirement: Virtual environment creation script

The system SHALL provide a script `scripts/create_venv.sh` that creates a Python virtual environment and installs the project with development dependencies in a single command.

### Requirement: Development services startup script

The system SHALL provide a script `scripts/dev.sh` that:
1. Starts Docker services (PostgreSQL, Redis, MinIO) in background
2. Waits for services to be healthy
3. Starts Django development server with hot reload

### Requirement: Service readiness wait script

The system SHALL provide a script `scripts/wait_for_services.sh` that blocks until all required services (PostgreSQL, Redis, MinIO) are accepting TCP connections.

### Requirement: Makefile development shortcuts

The system SHALL provide a Makefile with the following commands:
- `make dev` - Start full development environment
- `make dev.up` - Start Docker services only
- `make dev.run` - Start Django development server only
- `make test` - Run pytest
- `make lint` - Run ruff, black, and isort checks
- `make clean` - Remove __pycache__, .pyc, and other temporary files

### Requirement: Development environment configuration file

The system SHALL provide a `.env.development` file with default local development values for:
- DEBUG=True
- DATABASE_URL for localhost PostgreSQL
- REDIS_URL for localhost Redis
- CELERY_BROKER_URL

### Requirement: Docker Compose override for local development

The system SHALL provide `docker/docker-compose.override.yml` that:
- Mounts source code as volume for hot reload
- Enables DEBUG=True environment variable
- Configures health checks for PostgreSQL, Redis, and MinIO
- Uses `condition: service_healthy` for service dependencies

### Requirement: CONTRIBUTING.md documentation update

The documentation SHALL be updated to include:
- Simplified setup commands using new scripts and Makefile
- Prerequisites (Python 3.12+, Docker, Docker Compose)
- Quick start workflow

## MODIFIED Requirements

### Requirement: Django development settings

**FROM:**

The system SHALL NOT include development-specific Django settings.

**TO:**

The system SHALL include development-specific Django settings that:
- Set DEBUG=True when DEBUG environment variable is set
- Configure logging for DEBUG level in development environment
- Include development-friendly error pages

#### Scenario: DEBUG mode enabled
- **WHEN** DEBUG=True is set in environment
- **THEN** Django shall set DEBUG=True and configure verbose logging

#### Scenario: Development server with auto-reload
- **WHEN** Django runs with `python manage.py runserver`
- **THEN** changes to Python files shall trigger automatic server restart
