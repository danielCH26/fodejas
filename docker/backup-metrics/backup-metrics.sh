#!/bin/bash
# Backup job monitoring script
# Updates backup status metrics for Prometheus textfile collector

METRICS_DIR="/var/lib/node_exporter/textfile_collector"
METRICS_FILE="${METRICS_DIR}/backup_metrics.prom"

# Ensure metrics directory exists
mkdir -p "${METRICS_DIR}"

# Get backup timestamps from S3
S3_BUCKET="${S3_BUCKET:-fodejas-backups}"
S3_ENDPOINT="${S3_ENDPOINT:-http://minio:9000}"
S3_ACCESS_KEY="${S3_ACCESS_KEY:-minioadmin}"
S3_SECRET_KEY="${S3_SECRET_KEY:-minioadmin}"

mc alias set minio "${S3_ENDPOINT}" "${S3_ACCESS_KEY}" "${S3_SECRET_KEY}" 2>/dev/null || true

# Get latest base backup info
LATEST_BASE=$(mc ls "minio/${S3_BUCKET}/base/" 2>/dev/null | tail -n 1 | awk '{print $5}' || echo "none")
LATEST_BASE_TIME=$(mc ls "minio/${S3_BUCKET}/base/" 2>/dev/null | tail -n 1 | awk '{print $1,$2}' || echo "unknown")

# Get latest WAL archive info
LATEST_WAL=$(mc ls "minio/${S3_BUCKET}/wal/" 2>/dev/null | tail -n 1 | awk '{print $5}' || echo "none")
LATEST_WAL_TIME=$(mc ls "minio/${S3_BUCKET}/wal/" 2>/dev/null | tail -n 1 | awk '{print $1,$2}' || echo "unknown")

# Calculate backup age
CURRENT_TIME=$(date +%s)
if [ "${LATEST_BASE}" != "none" ]; then
    BACKUP_AGE=$((CURRENT_TIME - $(date +%s --date="${LATEST_BASE_TIME}" 2>/dev/null || echo "${CURRENT_TIME}")))
else
    BACKUP_AGE=86400  # Default to 24h if no backup
fi

# Determine status (0=success, 1=failed)
if [ "${LATEST_BASE}" != "none" ] && [ ${BACKUP_AGE} -lt 172800 ]; then  # 48 hours
    BACKUP_STATUS=0
else
    BACKUP_STATUS=1
fi

# Write Prometheus metrics
cat > "${METRICS_FILE}" << Metrics
# HELP backup_job_last_run_status Status of last backup job (0=success, 1=failed)
# TYPE backup_job_last_run_status gauge
backup_job_last_run_status ${BACKUP_STATUS}
# HELP backup_job_last_success_timestamp Unix timestamp of last successful backup
# TYPE backup_job_last_success_timestamp gauge
backup_job_last_success_timestamp $((CURRENT_TIME - BACKUP_AGE))
# HELP backup_latest_base_backup_name Name of latest base backup
# TYPE backup_latest_base_backup_name gauge
backup_latest_base_backup_name 1
# HELP backup_latest_wal_archive_name Name of latest WAL archive
# TYPE backup_latest_wal_archive_name gauge
backup_latest_wal_archive_name 1
Metrics

echo "Backup metrics updated at $(date)"
