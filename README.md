# FODEJAS

![CI](https://github.com/fodejas/fodejas/actions/workflows/ci.yml/badge.svg)
![Docker Build](https://github.com/fodejas/fodejas/actions/workflows/docker-build.yml/badge.svg)
![Deploy Staging](https://github.com/fodejas/fodejas/actions/workflows/deploy-staging.yml/badge.svg)
![Deploy Production](https://github.com/fodejas/fodejas/actions/workflows/deploy-production.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![Django](https://img.shields.io/badge/django-5.2-green.svg)

**FODEJAS** — Fondo para el Desarrollo Educativo de los Jóvenes del Archipiélago

Plataforma web Django para digitalizar el ciclo completo de las convocatorias de la Secretaría de Educación Departamental de San Andrés, Providencia y Santa Catalina.

## Funcionalidades

- Publicación de convocatorias
- Recepción de postulaciones
- Validación de requisitos
- Cálculo de puntajes
- Gestión de reclamaciones/apelaciones
- Emisión de actos administrativos
- Formalización de créditos
- Ordenamiento de pagos a Tesorería
- Seguimiento académico/psicosocial
- Gestión de condonaciones
- Informes y portal de transparencia

## Tech Stack

- **Backend**: Django 5, Django REST Framework
- **Base de datos**: PostgreSQL 16
- **Cache/Colas**: Redis + Celery
- **Frontend**: HTMX
- **PDF**: WeasyPrint
- **Storage**: S3-compatible (MinIO)
- **Docker**

## Quick Start

```bash
# Clonar repositorio
git clone <url>
cd fodejas

# Copiar configuración
cp .env.example .env

# Levantar servicios
docker compose -f docker/docker-compose.yml up -d

# Instalar dependencias
pip install -e ".[dev]"

# Instalar hooks
./scripts/setup.sh

# Migraciones
python manage.py migrate

# Servidor de desarrollo
python manage.py runserver
```

## Estructura del Proyecto

```
fodejas/
├── apps/              # Aplicaciones Django
│   ├── accounts/
│   ├── convocatories/
│   ├── applications/
│   ├── scoring/
│   └── ...
├── config/            # Configuración Django
├── docker/            # Dockerfiles y compose
├── openspec/          # Documentación OpenSpec
├── scripts/           # Scripts de utilidad
└── .github/           # GitHub Actions
```

## Licencia

[Ver LICENSE](LICENSE)
