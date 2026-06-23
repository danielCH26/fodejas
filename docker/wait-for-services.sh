#!/bin/bash
set -e

POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-fodejas_user}"
POSTGRES_DB="${POSTGRES_DB:-fodejas_db}"

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"

POSTGRES_TIMEOUT=60
REDIS_TIMEOUT=30
INTERVAL=2

echo "=== Waiting for services ==="

echo "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
elapsed=0
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER" -d "$POSTGRES_DB" > /dev/null 2>&1; do
  echo "PostgreSQL unavailable (${elapsed}s/${POSTGRES_TIMEOUT}s), retrying..."
  sleep $INTERVAL
  elapsed=$((elapsed + INTERVAL))
  if [ $elapsed -ge $POSTGRES_TIMEOUT ]; then
    echo "ERROR: PostgreSQL did not become available within ${POSTGRES_TIMEOUT} seconds"
    exit 1
  fi
done
echo "PostgreSQL is ready!"

echo "Waiting for Redis at ${REDIS_HOST}:${REDIS_PORT}..."
elapsed=0
if [ -n "$REDIS_PASSWORD" ]; then
  until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" -a "$REDIS_PASSWORD" ping > /dev/null 2>&1; do
    echo "Redis unavailable (${elapsed}s/${REDIS_TIMEOUT}s), retrying..."
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
    if [ $elapsed -ge $REDIS_TIMEOUT ]; then
      echo "ERROR: Redis did not become available within ${REDIS_TIMEOUT} seconds"
      exit 1
    fi
  done
else
  until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; do
    echo "Redis unavailable (${elapsed}s/${REDIS_TIMEOUT}s), retrying..."
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
    if [ $elapsed -ge $REDIS_TIMEOUT ]; then
      echo "ERROR: Redis did not become available within ${REDIS_TIMEOUT} seconds"
      exit 1
    fi
  done
fi
echo "Redis is ready!"

echo "=== All services ready ==="

exec "$@"
