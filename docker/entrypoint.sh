#!/bin/bash
set -e

echo "=== Running Django Entrypoint ==="

echo "Waiting for database..."
python manage.py wait_for_db || true

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput || true

echo "Entrypoint complete. Starting application..."

exec "$@"
