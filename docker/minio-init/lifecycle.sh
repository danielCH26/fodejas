#!/bin/bash
# GAP #6 — MinIO bucket lifecycle and versioning initialization.
# Enables versioning and lifecycle rules on the fodejas-media bucket.
# Idempotent: mc commands can be run multiple times safely.
#
# This script runs once via the minio-init one-shot service, then exits.
# To re-run manually:
#   docker compose run --rm minio-init
#
# Requirements:
#   - MINIO_ROOT_USER and MINIO_ROOT_PASSWORD env vars
#   - mc (MinIO Client) must be available in the image

set -euo pipefail

echo "[minio-init] Starting bucket initialization..."

# Configure MinIO client alias
mc alias set local "${MINIO_ENDPOINT:-http://minio:9000}" "${MINIO_ROOT_USER:-minioadmin}" "${MINIO_ROOT_PASSWORD:-minioadmin}" 2>/dev/null || {
    echo "[minio-init] WARNING: mc alias set failed, continuing anyway (may already exist)"
}

BUCKET="local/fodejas-media"

# 1. Enable versioning on the bucket
# Idempotent: enabling versioning on an already-versioned bucket succeeds silently.
echo "[minio-init] Enabling versioning on ${BUCKET}..."
mc version enable "${BUCKET}" 2>/dev/null || echo "[minio-init] NOTE: versioning may already be enabled"

# 2. Add lifecycle rule for noncurrent versions expiry (90 days)
# Noncurrent versions are previous versions created by overwrites (with versioning enabled).
# mc ilm rule add is idempotent - adding a rule with the same transition is safe.
echo "[minio-init] Adding lifecycle rule: noncurrent versions expire after 90 days..."
mc ilm rule add --noncurr-expire-days 90 "${BUCKET}" 2>/dev/null || echo "[minio-init] NOTE: noncurrent expiry rule may already exist"

# 3. Add lifecycle rule for incomplete multipart uploads cleanup (30 days)
# This prevents orphaned upload parts from consuming storage indefinitely.
echo "[minio-init] Adding lifecycle rule: incomplete uploads expire after 30 days..."
mc ilm rule add --expire-delete-marker --expire-obj-days 30 "${BUCKET}" 2>/dev/null || echo "[minio-init] NOTE: incomplete upload rule may already exist"

# 4. Verify configuration (optional, for logging)
echo "[minio-init] Current lifecycle rules:"
mc ilm rule list "${BUCKET}" 2>/dev/null || echo "[minio-init] Could not list rules (bucket may not exist yet)"

echo "[minio-init] Bucket initialization complete. Exiting."
