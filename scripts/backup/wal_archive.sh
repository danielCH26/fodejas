#!/bin/bash
set -e

# WAL Archive script for PostgreSQL
# Archives WAL segments to S3 (MinIO) for point-in-time recovery

S3_BUCKET="${S3_BUCKET:-fodejas-backups}"
S3_ENDPOINT="${S3_ENDPOINT:-http://minio:9000}"
S3_ACCESS_KEY="${S3_ACCESS_KEY:-minioadmin}"
S3_SECRET_KEY="${S3_SECRET_KEY:-minioadmin}"
WAL_DIR="${WAL_DIR:-/var/lib/postgresql/wal_archive}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Starting WAL archive process..."

mc alias set minio "${S3_ENDPOINT}" "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}" 2>/dev/null || true

mc mb "minio/${S3_BUCKET}" --ignore-existing 2>/dev/null || true

ARCHIVE_DIR="${WAL_DIR}/archive_${TIMESTAMP}"
mkdir -p "${ARCHIVE_DIR}"

if [ -n "$(ls -A ${WAL_DIR}/ 2>/dev/null)" ]; then
    cp "${WAL_DIR}/"* "${ARCHIVE_DIR}/" 2>/dev/null || true

    mc cp --recursive "${ARCHIVE_DIR}/" "minio/${S3_BUCKET}/wal/${TIMESTAMP}/"

    rm -rf "${ARCHIVE_DIR}"

    echo "WAL archive completed: ${TIMESTAMP}"
else
    echo "No WAL files to archive."
fi

echo "Cleaning up WAL archives older than 30 days..."
mc rm --recursive --force --older-than 30d "minio/${S3_BUCKET}/wal/" 2>/dev/null || true

echo "WAL archive process done."
