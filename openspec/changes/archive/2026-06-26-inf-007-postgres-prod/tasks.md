## 1. PostgreSQL Tuning Configuration

- [x] 1.1 Create `docker/postgres.conf` with production tuning parameters
- [x] 1.2 Configure `max_connections = 100`
- [x] 1.3 Configure `shared_buffers = 256MB`
- [x] 1.4 Configure `effective_cache_size = 768MB`
- [x] 1.5 Configure `maintenance_work_mem = 64MB`
- [x] 1.6 Configure checkpoint and SSD optimization parameters
- [x] 1.7 Update docker-compose to use custom postgres.conf

## 2. PgBouncer Setup

- [x] 2.1 Add PgBouncer service to `docker/docker-compose.yml`
- [x] 2.2 Create `docker/pgbouncer.ini` with transaction pooling mode
- [x] 2.3 Configure connection limits (max_client_conn=100, default_pool_size=20)
- [x] 2.4 Update `config/settings.py` to use PgBouncer in production
- [x] 2.5 Add health check endpoint for PgBouncer
- [x] 2.6 Test connection through PgBouncer

## 3. Backup Infrastructure

- [x] 3.1 Create S3 bucket `fodejas-backups` in MinIO
- [x] 3.2 Create `scripts/backup/base_backup.sh` script
- [x] 3.3 Configure WAL archiving to S3 in postgres.conf
- [x] 3.4 Create `scripts/backup/wal_archive.sh` script
- [x] 3.5 Create `scripts/backup/backup_verify.sh` script
- [x] 3.6 Add backup retention policy (7 days base, 30 days WAL)
- [x] 3.7 Create cron schedule or systemd timer for backups

## 4. Monitoring Setup

- [x] 4.1 Enable `pg_stat_statements` extension
- [x] 4.2 Create SQL view for slow queries analysis
- [x] 4.3 Add connection count metrics to Prometheus exporter
- [x] 4.4 Add cache hit ratio metrics
- [x] 4.5 Create Grafana dashboard for PostgreSQL metrics
- [x] 4.6 Add backup job monitoring alerts

## 5. Documentation

- [x] 5.1 Document backup/restore procedures in README
- [x] 5.2 Document PgBouncer connection troubleshooting
- [x] 5.3 Update CONTRIBUTING.md with production database setup
- [x] 5.4 Document connection string changes for staging/production

## 6. Testing and Validation

- [x] 6.1 Test backup/restore in staging environment
- [x] 6.2 Validate PgBouncer transaction mode with Django
- [x] 6.3 Verify Prometheus metrics are scraped correctly
- [x] 6.4 Load test with concurrent connections through PgBouncer
