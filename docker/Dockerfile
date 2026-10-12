# Stage 1: Build stage
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

COPY . .

# Stage 2: Production stage
FROM python:3.12-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libpq5 \
    bash \
    && rm -rf /var/lib/apt/lists/*

# Runtime deps live in site-packages (pip installs there, not in /app).
# /usr/local/bin trae los console-scripts (celery, gunicorn, ...).
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app .
# Windows checkouts leave CRLF in shell scripts -> normalize for the container.
RUN sed -i 's/\r$//' docker/*.sh

EXPOSE 8000

ENTRYPOINT ["docker/wait-for-services.sh", "python", "manage.py"]
# CHG-803 / AUD-018 — gunicorn is the production WSGI server.
# runserver is for local dev only (docker/docker-compose.yml's `app`
# service keeps the runserver command for that purpose). The prod
# override (docker/docker-compose.production.yml) pins the same
# command so the override is consistent even if this base CMD is
# changed later.
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-"]
