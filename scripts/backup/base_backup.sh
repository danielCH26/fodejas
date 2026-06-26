#!/bin/bash
set -e

# Base backup script for PostgreSQL
# Creates a full base backup and uploads to S3 (MinIO)

S3_BUCKET="${S3_BUCKET:-fodejas-backups}"
S3_ENDPOINT="${S3_ENDPOINT:-http://minio:9000}"
S3_ACCESS_KEY="${S3_ACCESS_KEY:-minioadmin}"
S3_SECRET_KEY="${S3_SECRET_KEY:-minioadmin}"
BACKUP_DIR="${BACKUP_DIR:-/tmp/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="base_backup_${TIMESTAMP}"

echo "Starting base backup: ${BACKUP_NAME}"

mkdir -p "${BACKUP_DIR}"

mc alias set minio "${S3_ENDPOINT}" "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}" 2>/dev/null || true

mc mb "minio/${S3_BUCKET}" --ignore-existing 2>/dev/null || true

BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

pg_basebackup -h "${PGHOST:-db}" -U "${PGUSER:-fodejas_user}" -D "${BACKUP_PATH}" -Ft -z -P

mc cp --recursive "${BACKUP_PATH}/" "minio/${S3_BUCKET}/base/${BACKUP_NAME}/"

echo "Base backup completed: ${BACKUP_NAME}"
echo "Uploading to s3://${S3_BUCKET}/base/${BACKUP_NAME}/"

rm -rf "${BACKUP_PATH}"

echo "Cleaning up backups older than 7 days..."
mc rm --recursive --force --older-than 7d "minio/${S3_BUCKET}/base/" 2>/dev/null || true

echo "Base backup done."
