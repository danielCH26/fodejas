# Monitoreo y Alertas — FODEJAS

> Prometheus + alertas operacionales. No hay Grafana en la versión actual.
> Referencia: roadmap.md INF-015.
>
> ⚠ **SLOs PROPUESTOS — NO APROBADOS:**
> Los valores de disponibilidad y latencia en este documento son
> **propuestos** y requieren aprobación institucional.

---

## 1. Endpoints de salud y métricas

### 1.1 `/healthz` — Liveness

- **URL:** `GET /healthz`
- **Propósito:** Indica si el proceso Django está vivo.
- **Siempre retorna 200** con `{"status": "ok"}`.
- **No checks** de dependencias (DB, Redis).
- **Uso:** El orquestador (Kubernetes, Docker Healthcheck) polling para saber
  si debe reiniciar el contenedor.

```bash
curl http://localhost:8000/healthz
# {"status": "ok"}
```

### 1.2 `/readyz` — Readiness

- **URL:** `GET /readyz`
- **Propósito:** Indica si la aplicación puede servir tráfico.
- **Checks:**
  - DB: `SELECT 1` con timeout 5s.
  - Redis: `redis.ping()` con timeout 5s.
- **Respuestas:**
  - `200 OK` + `{"status": "ok", "checks": {"database": "ok", "redis": "ok"}}`
  - `503 Service Unavailable` + `{"status": "unhealthy", "checks": {"database": "ok", "redis": "failed"}}`

```bash
curl http://localhost:8000/readyz
# {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}
```

### 1.3 `/metrics` — Prometheus

- **URL:** `GET /metrics`
- **Propósito:** Métricas Django (vistas, duración, errores) + métricas custom
  de Celery (`apps/core/celery_metrics.py`).
- **Formato:** Exposición Prometheus (OpenMetrics).
- **Requiere autenticación:** No (expuesto en red interna).

```bash
curl http://localhost:8000/metrics | head -30
```

---

## 2. Targets de Prometheus — Estado real

> **Archivo:** `docker/prometheus/prometheus.yml`

| Job | Target | Puerto | Estado real | Notas |
|---|---|---|---|---|
| `postgres` | `postgres-exporter:9187` | 9187 | ✅ Funcionando | Métricas vía `postgres_exporter` |
| `pgbouncer` | `pgbouncer-exporter:9631` | 9631 | ✅ Funcionando | Métricas vía `pgbouncer_exporter` |
| `backup-jobs` | `backup-exporter:9100` | 9100 | ✅ Existe (chore/ops-hardening) | Ver §4 — cerrado |

El contenedor `backup-exporter` **no está definido** en `docker-compose.yml`.
Prometheus está configurado para hacer scrape de él pero no existe.

---

## 3. Alertas Prometheus — Definiciones actuales

> **Archivo:** `docker/prometheus/alerts.yml`

### 3.1 PostgreSQL

| Alerta | Expresión | for | Severidad | Significado | Acción |
|---|---|---|---|---|---|
| `PostgresTooManyConnections` | `pg_stat_database_numbackends / pg_settings_max_connections > 0.8` | 5m | warning | >80% conexiones en uso | Revisar procesos activos |
| `PostgresConnectionNearLimit` | `pg_stat_database_numbackends / pg_settings_max_connections > 0.9` | 1m | **critical** | >90% conexiones | Escalar: conexiones al límite |
| `PostgresLowCacheHitRatio` | `pg_stat_database_blks_hit / (blks_hit + blks_read) < 0.90` | 5m | warning | Cache hit < 90% | Investigar queries que leen mucho disco |
| `PostgresSlowQueries` | `rate(pg_stat_statements_mean_exec_time_ms[5m]) > 1000` | 5m | warning | Queries con tiempo medio >1s | ✅ Funcional (chore/ops-hardening; caveat initdb en volúmenes existentes) |
| `PostgresDown` | `pg_up == 0` | 1m | **critical** | PostgreSQL no responde | Ir a [`03-incident-response.md`](03-incident-response.md) §2 |

### 3.2 PgBouncer

| Alerta | Expresión | for | Severidad | Significado | Acción |
|---|---|---|---|---|---|
| `PgBouncerPoolExhausted` | `pgbouncer_pools_server_active == server_active + server_idle` | 5m | warning | Pool saturado | Reducir carga o aumentar `default_pool_size` |
| `PgBouncerWaitingClients` | `pgbouncer_pools_cl_waiting > 0` | 5m | warning | Clientes esperando conexión | Similar a PoolExhausted |
| `PgBouncerDown` | `pgbouncer_up == 0` | 1m | **critical** | PgBouncer no responde | Restart pgbouncer |

### 3.3 Backups

| Alerta | Expresión | for | Severidad | Significado | Acción |
|---|---|---|---|---|---|
| `BackupJobFailed` | `backup_job_last_run_status == 0` | 5m | **critical** | Último job falló | **⚠ Puede ser false positive** (Gap #2) |
| `BackupNotRunning` | `time() - backup_job_last_success_timestamp > 86400 * 2` | 1h | **critical** | Sin backup exitoso en 48h | **⚠ Puede ser false positive** (Gap #2) |

---

## 4. Alertas corregidas (chore/ops-hardening)

> **ACTUALIZACIÓN:** los gaps #2 y #3 fueron cerrados en la rama
> `chore/ops-hardening`: servicio `backup-exporter` (node-exporter con
> textfile collector) añadido al compose, lógica invertida de
> `BackupJobFailed` corregida (el script escribe 0=éxito, 1=falla; la
> alerta decía `== 0`), y `pg_stat_statements` habilitado vía
> `shared_preload_libraries` + init script. Detalle histórico abajo.


### Gap #2: `BackupJobFailed` y `BackupNotRunning` no funcionan

**Problema:** El contenedor `backup-exporter:9100` no existe en
`docker-compose.yml`. El `backup-metrics.sh` escribe en un textfile
collector (`/var/lib/node_exporter/textfile_collector/backup_metrics.prom`)
dentro del contenedor `fodejas_backup_scheduler`, pero Prometheus no hace
scrape de él porque está configurado para el endpoint `backup-exporter:9100`.

**Evidencia:**
- `docker/prometheus/prometheus.yml` línea: `targets: ['backup-exporter:9100']`
- `docker-compose.yml`: No existe servicio `backup-exporter`.
- `docker/backup-metrics/crontab`: métricas solo disponibles internamente.

**Impacto operativo:** Las alertas de backup **siempre reportan el estado
del textfile collector del scheduler**, no del sistema de monitoreo.
Pueden dar falsos positivos o falsos negativos.

**Fix pendiente:** Crear el servicio `backup-exporter` en el compose
(usando `prom/node-exporter` con `--collector.textfile.directory` pointing
al volumen `backup_metrics`) y verificar que Prometheus haga scrape del
volumen correcto.

### Gap #3: `PostgresSlowQueries` siempre devuelve null

**Problema:** La extensión `pg_stat_statements` **no está habilitada**
en `docker/postgres.conf`.

**Evidencia:**
- `docker/postgres.conf` línea 52-54: No existe `shared_preload_libraries = 'pg_stat_statements'`.
- La expresión `rate(pg_stat_statements_mean_exec_time_ms[5m])` siempre es
  `NaN` porque la métrica no existe.

**Impacto operativo:** La alerta de queries lentas **no detecta nada**.

**Fix pendiente:** Agregar en `postgres.conf`:
```ini
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
```
Y reiniciar PostgreSQL. Luego verificar con:
```bash
docker compose exec db psql -U fodejas_user -d fodejas_db -c \
  "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 5;"
```

---

## 5. Logs estructurados JSON (producción)

### 5.1 Formato

En `DJANGO_ENV=production` los logs van a stdout en formato JSON
(vía `pythonjsonlogger` + `QueueHandler`/`QueueListener`):

```json
{
  "timestamp": "2024-12-01 09:15:23,456",
  "level": "ERROR",
  "name": "django.request",
  "module": "exception",
  "process": 42,
  "thread": 1398,
  "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "user_id": "admin",
  "path": "/admin/convocatorias/",
  "query_string": null,
  "message": "Unhandled exception"
}
```

### 5.2 Campos relevantes para operadores

| Campo | Descripción |
|---|---|
| `request_id` | UUID de la petición — buscar en todos los logs de la misma request |
| `user_id` | ID del usuario (si autenticado) — **nunca PII** |
| `path` | Ruta de la request (PII en query strings ya redactado) |
| `level` | DEBUG / INFO / WARNING / ERROR / CRITICAL |
| `module` | Módulo Python que generó el log |
| `message` | Mensaje (PII nunca va en message) |

### 5.3 Correlación de logs

```bash
# Buscar todos los logs de una request específica
docker compose logs app | grep "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

# Filtrar por nivel de error en producción
docker compose logs app | python -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        if d.get('level') in ('ERROR', 'CRITICAL'):
            print(f\"{d.get('timestamp')} [{d.get('level')}] req={d.get('request_id','')} {d.get('message','')}\")
    except:
        pass
"
```

---

## 6. Sentry (producción)

### 6.1 Configuración

```python
# config/settings.py
sentry_sdk.init(
    dsn=env("SENTRY_DSN", default=""),  # vacío en dev/staging
    integrations=[DjangoIntegration()],
    send_default_pii=False,              # CRÍTICO: no enviar PII
    environment=settings.DJANGO_ENV,
)
```

### 6.2 Qué reporta Sentry

| Evento | Reportado a Sentry |
|---|---|
| Excepciones no manejadas en vistas | ✅ Sí |
| Errores de Celery tasks | ✅ Sí |
| Errores en commands de management | ✅ Sí |
| Logs de nivel ERROR/CRITICAL | ⚠ Solo si `sentry_sdk.capture_message()` explícito |
| Datos personales (passwords, tokens, nombres completos) | ❌ **Nunca** (`send_default_pii=False`) |
| Request bodies | ❌ No (reducido por `send_default_pii=False`) |

### 6.3 Cómo usar Sentry en un incidente

1. Acceder a Sentry con credenciales institucionales.
2. Buscar por `user_id` anonymizado (IDs numéricos) o `request_id`.
3. Ver el stack trace, ambiente, y última release desplegada.
4. Asignar issue al developer responsable.

---

## 7. SLOs — VALORES PROPUESTOS (NO APROBADOS)

> ⚠ Estos valores requieren aprobación institucional antes de go-live.

| SLO | Métrica | Valor propuesto | Período | Notas |
|---|---|---|---|---|
| Disponibilidad | `% de requests con 2xx/3xx sobre total` | **≥ 99.0%** | Mensual | Equivale a ~7.3h downtime/mes |
| Disponibilidad | Endpoint `/readyz` = 200 | **≥ 99.5%** | Mensual | - |
| Latencia p50 | Tiempo de respuesta median | **< 500 ms** | Mensual | Base de línea en staging |
| Latencia p95 | Tiempo de respuesta 95th percentile | **< 2000 ms** | Mensual | Objetivo operador |
| Latencia p99 | Tiempo de respuesta 99th percentile | **< 5000 ms** | Mensual | Objetivo operador |
| Tareas Celery | `% tareas completadas sin error` | **≥ 99.0%** | Semanal | Beat + Worker |
| Backups | `% días con base backup exitoso` | **≥ 95.0%** | Mensual | (con Gap #2 activo, medir manualmente) |

### Error budget (propuesto)

Si el SLO de disponibilidad es 99% mensual:
- **Error budget:** 1% de ~43,200 minutos/mes = **432 minutos (~7.2 horas)**
- Si se consume > 50% del error budget en un mes → revisar arquitectura.

---

## 8. Tabla resumen de métricas disponibles

| Métrica | Fuente | Scraped? | Alerta? | Confiable? |
|---|---|---|---|---|
| `pg_stat_database_*` | postgres-exporter:9187 | ✅ | ✅ (varias) | ✅ |
| `pg_settings_*` | postgres-exporter:9187 | ✅ | ✅ | ✅ |
| `pg_stat_statements_mean_exec_time_ms` | postgres-exporter:9187 | ✅ | ⚠ (siempre NaN) | ❌ — extensión no habilitada |
| `pgbouncer_*` | pgbouncer-exporter:9631 | ✅ | ✅ (varias) | ✅ |
| `backup_job_last_run_status` | backup-metrics.sh → textfile | ❌ (Gap #2) | ⚠ | ❌ |
| `backup_job_last_success_timestamp` | backup-metrics.sh → textfile | ❌ (Gap #2) | ⚠ | ❌ |
| Métricas Django | /metrics | ✅ | ❌ (no configuradas) | ✅ |
| Celery metrics | /metrics | ✅ | ❌ (no configuradas) | ✅ |

---

Anterior: [`03-incident-response.md`](03-incident-response.md)
|
Siguiente: [`05-known-gaps.md`](05-known-gaps.md)
