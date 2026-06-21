#!/bin/bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

if [ -f ".env.development" ]; then
    export $(cat .env.development | grep -v '^#' | xargs)
fi

echo "Starting Docker services..."
docker compose -f docker/docker-compose.yml -f docker/docker-compose.override.yml up -d

echo "Waiting for services to be healthy..."
./scripts/wait_for_services.sh -t 60

echo "Starting Django development server..."
python manage.py runserver 0.0.0.0:8000
