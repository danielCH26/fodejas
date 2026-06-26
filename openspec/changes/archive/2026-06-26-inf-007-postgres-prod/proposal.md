## Why

FODEJAS necesita infraestructura de base de datos robusta para producción. Actualmente usa PostgreSQL sin configuración de producción optimizada, lo que puede causar problemas de rendimiento bajo carga y no tiene estrategias de recuperación ante desastres.

## What Changes

- Configurar PostgreSQL de producción con parámetros de tuning optimizados (memory, connections, checkpoints)
- Implementar PgBouncer como connection pooler para reducir overhead de conexiones
- Configurar backups automatizados ( WAL archiving + base backups )
- Agregar extensiones de monitoreo (pg_stat_statements, pgbadger/pgwatch)
- Configurar replication para HA (opcional, documentar procedimiento)

## Capabilities

### New Capabilities

- `postgres-tuning`: Parámetros optimizados de PostgreSQL para producción
- `postgres-pooling`: PgBouncer connection pooling
- `postgres-backup`: Estrategia de backups automatizados
- `postgres-monitoring`: Extensiones y dashboards de monitoreo

### Modified Capabilities

- Ninguno (no cambia specs existentes)

## Impact

- Archivos de configuración:
  - `docker/postgres.conf` — tuning de PostgreSQL
  - `docker/pgbouncer.ini` — configuración PgBouncer
  - `scripts/backup.sh` — script de backup automatizado
  - `docker/docker-compose.yml` — actualizar para incluir PgBouncer
- Modificados:
  - `config/settings.py` — ajustar DATABASE_URL para PgBouncer
  - `.env.production.example` — agregar variables de PgBouncer
- Dependencias nuevas: `pgbouncer` (Docker), `pg_stat_statements` extension

## Constraints

- **No implementar replication master-slave** — Requiere infraestructura adicional, documentar solo
- **Backups a S3** — Usar MinIO existente del proyecto (compatibilidad S3)
- **PgBouncer en modo transaction** — Preferido para Django (conexiones cortas)
- **Sin impacto en desarrollo local** — Solo afecta entorno staging/production
