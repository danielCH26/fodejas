## Context

El proyecto FODEJAS usa Django 5 + PostgreSQL 16 + Redis + Celery + MinIO (S3-compatible).
El setup actual (inf-001-repo-bootstrap) deja la creación del entorno virtual y configuración
de desarrollo local a responsabilidad de cada desarrollador, generando fricción y
configuración inconsistente.

## Goals / Non-Goals

**Goals:**
- Automatizar la creación del entorno virtual Python con dependencias dev
- Proporcionar scripts para levantar servicios auxiliares (Postgres, Redis, MinIO) via Docker
- Habilitar hot reload nativo de Django sin necesidad de Docker para el proceso web
- Reducir tiempo de onboarding a minutos con comandos consistentes
- Centralizar configuración de desarrollo local en `.env.development`

**Non-Goals:**
- No se modifica la configuración de producción (solo desarrollo local)
- No se integra con sistemas externos (SNIES, SISBÉN, bancos)
- No se crea infraestructura como código para despliegue
- No se automatiza el provisionamiento de la base de datos

## Decisions

### 1. Script `scripts/create_venv.sh`

**Decisión:** Crear script Bash que automatiza la creación del entorno virtual.

**Alternativas consideradas:**
- Usar `python -m venv` directo (requiere que cada dev recuerde comandos)
- Usar `virtualenvwrapper` (dependencia externa, curva de aprendizaje)
- Usar `uv` o `pipenv` (nuevas herramientas, compatibilidad incierta con el stack)

**Elección:** Bash script simple con `python3 -m venv .venv && pip install -e ".[dev]"`

**Justificación:** Mínimo denominador común, funciona en cualquier sistema con Python 3.12+,
no introduce nuevas dependencias de herramientas.

### 2. Script `scripts/dev.sh`

**Decisión:** Script que levanta servicios Docker y ejecuta Django con hot reload.

**Alternativas consideradas:**
- Todo en Docker (docker-compose up) — complica debugging y hot reload
- Makefile solo — verboso para comandos complejos con depends_on
- Wrapper Python — overkill para el caso de uso

**Elección:** Bash script que:
1. Levanta servicios Docker en background (`docker compose up -d`)
2. Espera a que servicios estén healthy (via `wait_for_services.sh`)
3. Ejecuta `python manage.py runserver` con DEBUG=True

**Justificación:** Separa concerns (infraestructura Docker vs aplicación Python), facilita
debugging directo del proceso Django.

### 3. Script `scripts/wait_for_services.sh`

**Decisión:** Esperar a que PostgreSQL, Redis y MinIO estén disponibles antes de iniciar Django.

**Alternativas consideradas:**
- `depends_on` con `condition: service_healthy` en docker-compose — solo funciona entre contenedores
- `pg_isready`, `redis-cli ping` — comandos específicos por servicio
- `wait-for-it.sh` o similar — dependencia externa

**Elección:** Script propio que usa `nc` (netcat) para verificar puertos TCP.

**Justificación:** Sin dependencias externas, funciona para cualquier servicio TCP.

### 4. Makefile con comandos de desarrollo

**Decisión:** Crear Makefile con shortcuts para operaciones comunes.

**Comandos propuestos:**
- `make dev` — levantar entorno completo (Docker + Django)
- `make dev.up` — solo Docker services
- `make dev.run` — solo Django runserver
- `make test` — ejecutar pytest
- `make lint` — ejecutar ruff, black, isort
- `make clean` — limpiar archivos temporales y __pycache__

**Justificación:** Conveniencia, coherencia con otras herramientas DevOps, fácil discovery
de comandos disponibles.

### 5. `.env.development`

**Decisión:** Archivo con configuración local por defecto (no se commitea a git).

**Variables:**
```
DEBUG=True
DATABASE_URL=postgres://fodejas_user:fodejas_password@localhost:5432/fodejas_db
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
```

**Justificación:** Django-environ compatible, override de .env.example para desarrollo local.

### 6. docker-compose.override.yml improvements

**Decisión:** Agregar health checks y volumes para hot reload.

**Cambios:**
- Agregar `healthcheck` a PostgreSQL, Redis, MinIO
- Agregar `condition: service_healthy` en depends_on
- Volumes montados para hot reload: `..:/app`

**Justificación:** El stack actual ya tiene volumes, se mejora la robustness con health checks.

### 7. Django settings para development

**Decisión:** Agregar configuración de logging Development y auto-reload.

**Cambios en config/settings/:**
- `DEBUG = env.bool("DEBUG", default=True)`
- Logging configurado para DEVELOPMENT con уровень DEBUG
- `INTERNAL_IPS` para Django debug toolbar (si se instala)

**Justificación:** Logging detallado en desarrollo facilita troubleshooting.

## Risks / Trade-offs

| Risk | Mitigation |
|------|------------|
| El script Bash no funciona en Windows | Documentar WSL2 como alternativa, script es idempotente |
| Puerto 5432 ocupado por otra instancia Postgres | El script verifica y falla con mensaje claro |
| Permisos de ejecución en scripts | `chmod +x` en git hooks o documentación |
| .env.development sobreescribe .env.example | .env.example es template, .env.development es local |

## Migration Plan

1. Merge del change a `develop`
2. Documentación en CONTRIBUTING.md actualizada
3. Cada desarrollador ejecuta `./scripts/create_venv.sh` una vez
4. Para desarrollo: `make dev` o `./scripts/dev.sh`
5. No requiere migración de datos ni rollback

## Open Questions

1. ¿Se debe incluir Django Debug Toolbar en `.[dev]` dependencies?
   - **Decision:** No incluir por default, dejar a elección del desarrollador
2. ¿Soporte para Windows (PowerShell)?
   - **Decision:** Documentar WSL2 como requisito en CONTRIBUTING.md
