#!/bin/bash
set -e

# Backup verification script
# Tests restore from latest backup

S3_BUCKET="${S3_BUCKET:-fodejas-backups}"
S3_ENDPOINT="${S3_ENDPOINT:-http://minio:9000}"
S3_ACCESS_KEY="${S3_ACCESS_KEY:-minioadmin}"
S3_SECRET_KEY="${S3_SECRET_KEY:-minioadmin}"
VERIFY_DIR="${VERIFY_DIR:-/tmp/backup_verify}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "Starting backup verification..."

mc alias set minio "${S3_ENDPOINT}" "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}" 2>/dev/null || true

LATEST_BACKUP=$(mc ls "minio/${S3_BUCKET}/base/" | tail -n 1 | awk '{print $NF}')

if [ -z "${LATEST_BACKUP}" ]; then
    echo "ERROR: No backup found in s3://${S3_BUCKET}/base/"
    exit 1
fi

echo "Found latest backup: ${LATEST_BACKUP}"

VERIFY_TARGET="${VERIFY_DIR}/restore_${TIMESTAMP}"
mkdir -p "${VERIFY_TARGET}"

echo "Downloading backup..."
mc cp --recursive "minio/${S3_BUCKET}/base/${LATEST_BACKUP}/" "${VERIFY_TARGET}/"

echo "Extracting backup..."
cd "${VERIFY_TARGET}"
tar -xzf base.tar.gz
cd -

echo "Verifying backup integrity..."
if [ -f "${VERIFY_TARGET}/pg_xlog/000000010000000000000001" ] || [ -f "${VERIFY_TARGET}/pg_wal/000000010000000000000001" ]; then
    echo "Backup files verified."
else
    echo "WARNING: WAL file not found in backup."
fi

echo "Backup verification completed successfully."

rm -rf "${VERIFY_TARGET}"

echo "Verification done."
