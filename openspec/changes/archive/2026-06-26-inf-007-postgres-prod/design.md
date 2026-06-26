## Context

FODEJAS usa PostgreSQL como base de datos principal. Actualmente la configuración es básica sin tuning de producción, lo que puede causar:
- Alto uso de memoria con muchas conexiones
- Queries lentas sin visibilidad
- Sin estrategia de backups automatizados
- Riesgo de pérdida de datos ante fallos

El equipo de operaciones necesita una base de datos robusta y monitoreable.

## Goals / Non-Goals

**Goals:**
- Configurar PostgreSQL con parámetros optimizados para producción
- Implementar PgBouncer para connection pooling eficiente
- Establecer estrategia de backups automatizados (WAL + base backup)
- Agregar monitoreo de queries lentas y estadísticas
- Documentar procedimientos de recovery

**Non-Goals:**
- No implementar replication master-slave (futuro)
- No implementar auto-scaling de PostgreSQL
- No modificar el schema de la base de datos
- No cambiar el ORM o queries de la aplicación

## Decisions

### 1. Connection Pooling con PgBouncer

**Decisión:** Usar PgBouncer en modo transaction.

**Alternativas:**
- PgBouncer session mode — conexiones persistentes, más overhead
- PgBouncer statement mode — muy restrictivo, incompatible con Django
- Django-db-pool — no maduro, menos control

**Elección:** PgBouncer transaction mode.

**Justificación:** Django hace conexiones cortas, transaction mode es óptimo. Reduce conexiones a PostgreSQL de cientos a decenas.

### 2. Tuning de PostgreSQL

**Parámetros principales:**
```ini
max_connections = 100          # Reducido por PgBouncer
shared_buffers = 256MB          # 25% RAM para PostgreSQL
effective_cache_size = 768MB    # 75% RAM disponible
maintenance_work_mem = 64MB
wal_buffers = 16MB
checkpoint_completion_target = 0.9
random_page_cost = 1.1          # SSD-optimized
effective_io_concurrency = 200
```

**Justificación:** Optimizado para VPS/cloud con RAM limitada.

### 3. Estrategia de Backups

**Decisión:** Backup base diario + WAL continuo.

**Componentes:**
- `pg_basebackup` diario a S3 (MinIO)
- WAL archiving continuo a S3
- Retención: 7 días base backups, 30 días WAL

**Alternativas:**
- Barman — más complejo, overkill para este caso
- pgBackRest — similar pero más features enterprise
- Solo pg_dump — no point-in-time recovery

**Elección:** pg_basebackup + WAL + S3.

**Justificación:** Permite point-in-time recovery, usa MinIO existente.

### 4. Monitoreo

**Decisión:** Extensiones nativas + scripts de exportación.

**Extensiones:**
- `pg_stat_statements` — queries más lentas
- `pg_stats` — estadísticas de tablas
- `pg_stat_activity` — conexiones activas

**Métricas a exportar:**
- Query latency (p50, p95, p99)
- Connection count
- Cache hit ratio
- Replication lag (para futuro)

**Justificación:** Sin agente adicional, usa extensiones PostgreSQL nativas.

## Risks / Trade-offs

| Risk | Mitigation |
|------|-------------|
| PgBouncer breaking transactions | Usar transaction mode con Django, evitar prepared statements |
| Backups corruptos | Test de restore mensualmente, verificar integrity |
| WAL accumulation | Lifecycle policy en S3, cleanup automático |
| Queries lentas no detectadas | pg_stat_statements + alertas en Grafana |

## Migration Plan

1. Agregar configuración PgBouncer a docker-compose
2. Actualizar DATABASE_URL en staging para usar PgBouncer
3. Implementar y validar backups en staging
4. Configurar monitoreo con dashboards
5. Probar failover manual
6. Desplegar a producción con maintenance window

**Rollback:** Cambiar DATABASE_URL apuntando directo a PostgreSQL.

## Open Questions

1. **¿Cuántas conexiones necesita Django?**
   - Calcular según workers de Gunicorn/Celery
   - **Decisión**: Max 50 conexiones PostgreSQL via PgBouncer

2. **¿S3 o MinIO para backups?**
   - MinIO ya está configurado en el proyecto
   - **Decisión**: Usar bucket dedicado `fodejas-backups` en MinIO existente

3. **¿Retención de backups?**
   - Base backups: 7 días
   - WAL: 30 días
   - **Decisión**: Implementar lifecycle policy en MinIO
