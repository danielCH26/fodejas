#!/bin/bash
set -e

echo "=== Running Django Entrypoint ==="

docker/wait-for-services.sh python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Entrypoint complete. Starting application..."

exec "$@"
