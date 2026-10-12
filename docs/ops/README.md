# Ops — FODEJAS

> Entregables INF-011 (DRP), INF-012 (runbooks), INF-015 (monitoring).
> Rama: `feat/CHG-507-multilang`.

## Mapa de documentos

| Situación | Documento a leer |
|---|---|
| Necesito hacer un deploy | → [`01-deploy-runbook.md`](01-deploy-runbook.md) |
| Necesito restaurar un backup o responder a un desastre | → [`02-backup-disaster-recovery.md`](02-backup-disaster-recovery.md) |
| Algo se cayó o está fallando | → [`03-incident-response.md`](03-incident-response.md) |
| Hay alertas en Prometheus o quiero saber el estado de los servicios | → [`04-monitoring-alerts.md`](04-monitoring-alerts.md) |
| Quiero saber qué está roto hoy mismo | → [`05-known-gaps.md`](05-known-gaps.md) |

## Tabla de servicios Docker

| Servicio | Contenedor | Puerto(s) | Rol |
|---|---|---|---|
| app | `fodejas_app` | 8000 | Aplicación Django (runserver dev / gunicorn staging+prod) |
| celery-worker | `fodejas_celery_worker` | — | Tareas asíncronas (beat programa las schedules) |
| celery-beat | `fodejas_celery_beat` | — | Programador de tareas Celery Beat |
| postgres | `fodejas_db` | 5432 | Base de datos PostgreSQL 16 |
| pgbouncer | `fodejas_pgbouncer` | 6432 | Pool de conexiones (staging/prod) |
| redis | `fodejas_redis` | 6379 | Broker Celery + caché |
| minio | `fodejas_minio` | 9000 (API), 9001 (console) | Object storage (dev/staging) |
| postgres-exporter | `fodejas_postgres_exporter` | 9187 | Métricas Prometheus para PostgreSQL |
| pgbouncer-exporter | `fodejas_pgbouncer_exporter` | 9631 | Métricas Prometheus para PgBouncer |
| prometheus | `fodejas_prometheus` | 9090 | Recolección y almacenamiento de métricas |
| backup-scheduler | `fodejas_backup_scheduler` | — | Cron de backups (base, WAL, verify, metrics) |

**No existe el contenedor `backup-exporter` en esta rama.** Esto provoca que las alertas
`BackupJobFailed` y `BackupNotRunning` en Prometheus no funcionen correctamente.
Ver [`05-known-gaps.md`](05-known-gaps.md) Gap #2.

## Comandos rápidos de operador

```bash
# Estado de todos los servicios
docker compose ps

# Logs del app (follow)
docker compose logs -f app

# Logs del app (últimas 100 líneas)
docker compose logs --tail=100 app

# Verificar liveness (siempre 200 OK)
curl http://localhost:8000/healthz

# Verificar readiness (checks DB + Redis, 5s timeout)
curl http://localhost:8000/readyz

# Métricas Prometheus
curl http://localhost:9090/metrics | grep -E "pg_stat_database|backup_job"

# Consola MinIO
open http://localhost:9001  # user: minioadmin / pass: minioadmin

# Shell Django (dentro del contenedor)
docker compose exec app python manage.py shell

# Verificar cadena de auditoría (desde shell Django)
docker compose exec app python manage.py shell -c \
  "from apps.audit.services import verify_chain; print(verify_chain())"

# Estado de Celery (revisa tareas activas y reservadas)
docker compose exec celery-worker celery -A config inspect stats
```

## Roles operativos

| Rol | Permisos | Quién lo ejecuta |
|---|---|---|
| R-ADMIN | Superusuario, `verify_chain`, acceso total al admin | Operador de sistemas, Líder técnico |
| Superusuario Django | Equivale a R-ADMIN en la plataforma | Administrador de plataforma |

## Convenciones usadas en estos documentos

- Todo lo marcado `PROPUESTO` requiere aprobación institucional antes de ser política oficial.
- Los valores RTO y RPO son **propuestos**, no aprobados. Ver [`02-backup-disaster-recovery.md`](02-backup-disaster-recovery.md).
- Los SLOs de disponibilidad y latencia son **propuestos**. Ver [`04-monitoring-alerts.md`](04-monitoring-alerts.md).
- **Nunca** hacer rollback de migraciones destructivas. Las migraciones solo avanzan (forward-only).
- **Nunca** borrar eventos de la cadena de auditoría aunque esté rota.
- No incluir datos personales en ningún log ni comando ops.

---

Siguiente: [`01-deploy-runbook.md`](01-deploy-runbook.md)
