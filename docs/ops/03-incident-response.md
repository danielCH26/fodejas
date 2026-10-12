# Respuesta a Incidentes — FODEJAS

> Procedimientos operativos para incidentes comunes.
> Referencia: roadmap.md INF-012.

---

## Convenciones de severidad

| Severidad | Descripción | Tiempo de respuesta objetivo |
|---|---|---|
| **P1 — Crítica** | Servicio completamente caído, pérdida de datos confirmada, brecha de seguridad | Inmediato (< 15 min) |
| **P2 — Alta** | Funcionalidad principal degradada, backup fallando, alerta de disco | < 1 hora |
| **P3 — Media** | Funcionalidad secundaria degradada, degradación de performance | < 4 horas |
| **P4 — Baja** | Incidentes menores, alertas no accionables (gaps conocidos) | < 24 horas o siguiente día hábil |

---

## 1. App caída o respondiendo con errores 5xx

**Síntoma:** `curl -f http://localhost:8000/readyz` devuelve 503 o timeout.

### Diagnóstico

```bash
# 1. Verificar readiness completo
curl -s http://localhost:8000/readyz | python -m json.tool

# 2. ¿Qué check falló?
#    - "database": "failed" → ir a §2 (DB inaccesible)
#    - "redis": "failed"    → ir a §3 (Redis caído)

# 3. Logs del app (buscar errores)
docker compose logs --tail=200 app | grep -iE "error|exception|traceback"

# 4. ¿Gunicorn arrancado? (producción)
docker compose exec app ps aux | grep gunicorn

# 5. ¿Docker sigue corriendo?
docker compose ps
```

### Acción

```bash
# Si DB o Redis: resolver primero (ver §2 o §3).

# Si el app no responde pero DB y Redis OK:
docker compose restart app

# Si el app sigue fallando tras restart, revisar logs detallados:
docker compose logs -f app

# Si es un error de migrate (migration faltante):
docker compose exec app python manage.py migrate --noinput
docker compose restart app
```

### Verificación

```bash
curl -f http://localhost:8000/readyz
# Esperado: {"status": "ok", "checks": {"database": "ok", "redis": "ok"}}

curl -f http://localhost:8000/healthz
# Esperado: {"status": "ok"}
```

**Escalar a P1** si el servicio no está disponible en producción tras 30 min.

---

## 2. Base de datos PostgreSQL inaccesible

**Síntoma:** `readyz` reporta `database: failed`; `pg_isready` falla.

### Diagnóstico

```bash
# 1. ¿PostgreSQL está corriendo?
docker compose ps db

# 2. ¿Responde pg_isready?
docker compose exec db pg_isready -U fodejas_user -d fodejas_db
# Esperado: "accepting connections"

# 3. ¿PgBouncer estábloqueando conexiones?
docker compose exec pgbouncer sh -c "echo 'show pools;' | psql -h pgbouncer -U fodejas_user -d fodejas_db -p 6432"

# 4. ¿Logs de PostgreSQL?
docker compose logs --tail=100 db | grep -iE "error|fatal|cannot|reject"

# 5. ¿Espacio en disco?
docker compose exec db df -h

# 6. ¿Conexiones al límite?
docker compose exec db psql -U fodejas_user -d fodejas_db -c \
  "SELECT count(*) FROM pg_stat_activity WHERE state='active';"
docker compose exec db psql -U fodejas_user -d fodejas_db -c "SHOW max_connections;"
```

### Acción según diagnóstico

```bash
# Caso A: PostgreSQL no arranca — revisar logs
docker compose logs db | tail -50

# Caso B: Conexiones al límite (max_connections)
#   → Reducir carga: detener celery-worker temporalmente
docker compose stop celery-worker celery-beat
#   → Esperar que las conexiones inactivas se liberen (~1 min)
#   → Restart celery
docker compose up -d celery-worker celery-beat

# Caso C: Disco lleno en el volumen de PostgreSQL
#   → Ver qué ocupa espacio
docker compose exec db du -sh /var/lib/postgresql/data/
#   → Limpiar WAL locales si hay acumulado (no afectan restore):
docker compose exec db sh -c 'rm -rf /var/lib/postgresql/wal_archive/archive_*'
#   → Si el data dir está lleno: CRÍTICO → escalar P1 y considerar restore

# Caso D: PgBouncer rechazando conexiones
#   → Verificar que auth_type en pgbouncer.ini coincide con contraseñas
docker compose logs pgbouncer | grep -iE "login|auth|error"
```

### Verificación

```bash
docker compose exec db pg_isready -U fodejas_user -d fodejas_db
curl -f http://localhost:8000/readyz
```

**Escalar a P1** si PostgreSQL no arranca tras 15 min.

---

## 3. Redis caído — Celery detenido

**Síntoma:** `readyz` reporta `redis: failed`; tareas Celery no se ejecutan.

### Impacto

- **Beat se detiene silenciosamente** cuando Redis no responde.
- Las 6 tareas programadas (tesorería 09:00, exoneración 09:05, habeas 09:15)
  no se ejecutarán mientras Redis esté caído.
- **Protección:** Las tareas son idempotentes (`last_alerted_at` + audit sentinel).
  Al recuperar Redis y reiniciar Beat, las tareas del día en curso
  retomarán su schedule sin duplicar alertas.

### Diagnóstico

```bash
# 1. ¿Redis está corriendo?
docker compose ps redis

# 2. ¿Redis responde?
docker compose exec redis redis-cli ping
# Esperado: PONG

# 3. ¿Error de conexión?
docker compose logs --tail=50 redis

# 4. ¿Logs de Celery Worker?
docker compose logs --tail=50 celery-worker | grep -iE "refused|disconnect|error"
```

### Acción

```bash
# Redis caído → restart
docker compose restart redis

# Verificar que responde
sleep 5
docker compose exec redis redis-cli ping

# Reiniciar Celery (Beat se reinicia solo con restart, Worker necesita restart manual)
docker compose restart celery-worker celery-beat

# Verificar que Celery se reconectó
docker compose exec celery-worker celery -A config inspect stats
```

### Verificación

```bash
curl -f http://localhost:8000/readyz
# Esperado: redis: ok

# Verificar tareas beat registradas
docker compose exec celery-beat celery -A config inspect scheduled | \
  python -c "import sys,json; d=json.load(sys.stdin); [print(k) for k in d.get('tzdata',{}).get('Scheduler',{}).get('entries',{}).keys() or []]"
```

**Escalar a P2** si Redis no levanta tras 10 min.

---

## 4. Backups fallando

**Síntoma:** Alerta `BackupJobFailed` o `BackupNotRunning` en Prometheus,
o `backup_verify.sh` reporta error.

> ⚠ **NOTA:** Estas alertas pueden ser **false positives** debido al
> Gap #2 (backup-exporter no existe). Verificar primero con los
> comandos de diagnóstico antes de escalar.

### Diagnóstico

```bash
# 1. ¿Hay métrica de backup?
curl -s http://localhost:9090/metrics | grep backup_job
# Si la métrica NO existe → Gap #2 confirmado, no hay backup-exporter

# 2. Verificar logs del backup-scheduler
docker compose logs --tail=100 backup-scheduler

# 3. ¿El base backup se ejecutó?
mc ls minio/fodejas-backups/base/ | tail -5

# 4. ¿Los WAL se están archivando?
mc ls minio/fodejas-backups/wal/ | tail -5

# 5. ¿backup_verify.sh tiene errores?
docker compose logs backup-scheduler | grep backup_verify
```

### Acción

```bash
# Ejecutar base backup manualmente para verificar
docker compose exec backup-scheduler /scripts/backup/base_backup.sh

# Si falla, verificar:
#   a) PostgreSQL accesible: docker compose exec backup-scheduler nc -zv db 5432
#   b) MinIO accesible:       docker compose exec backup-scheduler nc -zv minio 9000
#   c) Credenciales MinIO:   revisar S3_ACCESS_KEY / S3_SECRET_KEY en compose

# Si las credenciales están bien y el backup manual funciona:
#   → El problema es el cron. Reiniciar el scheduler:
docker compose restart backup-scheduler

# Si MinIO no está reachable: verificar que el contenedor minio está corriendo
docker compose ps minio
```

### Verificación

```bash
# Tras ejecutar base backup manualmente:
mc ls minio/fodejas-backups/base/
# Debe aparecer el backup reciente

# Ejecutar verify manualmente:
docker compose exec backup-scheduler /scripts/backup/backup_verify.sh
# Esperado: "Backup verification completed successfully."
```

**Escalar a P2** si los backups no se restauran tras 1 hora de intervención.

---

## 5. Cadena de auditoría rota

**Síntoma:** `verify_chain()` devuelve `is_valid: false` con un `break_point`.

### Diagnóstico

```bash
# Ejecutar verificación
docker compose exec app python manage.py shell -c \
  "from apps.audit.services import verify_chain; import json; print(json.dumps(verify_chain(), indent=2))"

# Resultado ejemplo (roto):
# {
#   "is_valid": false,
#   "last_valid_hash": "abc123...",
#   "break_point": "<UUID del evento corrupto>"
# }
```

### Interpretación

- `is_valid: false` → Hay un evento cuyo hash no coincide con el calculado,
  o cuyo `previous_hash` no coincide con el evento anterior.
- `break_point` → UUID del primer evento corrupto detectado.
- `last_valid_hash` → Hash del último evento válido (antes del break_point).

### Qué hacer y qué NO hacer

| Acción | ¿Permitida? |
|---|---|
| Consultar `verify_chain()` para diagnosticar | ✅ Siempre |
| Revisar el evento en `/admin/audit/auditevent/` | ✅ Sí |
| **Borrar eventos de la cadena** | ❌ **NUNCA** — destruiría la cadena hash |
| **Modificar el hash de un evento manualmente** | ❌ **NUNCA** — rompería la cadena aguas abajo |
| **Eliminar y recrear la base de datos de auditoría** | ❌ **NUNCA** salvo que sea un incidente de seguridad |
| Escalar al líder técnico para investigación | ✅ **Sí — siempre** |

### Escalado e investigación

1. **Registrar el break_point** (UUID) y el `last_valid_hash`.
2. **Escalar al líder técnico** con:
   - Output completo de `verify_chain()`.
   - Log de los últimos eventos antes del break_point:
     ```bash
     docker compose exec app python manage.py shell -c "
     from apps.audit.models import AuditEvent
     from apps.audit.services import verify_chain
     result = verify_chain()
     # Mostrar eventos antes del break_point
     if result['break_point']:
         events = AuditEvent.objects.filter(id__lt=result['break_point']).order_by('-timestamp')[:5]
         for e in events:
             print(e.id, e.timestamp, e.action, e.entity, e.current_hash[:8])
     "
     ```
3. **Si la ruptura fue por ataque o brecha de seguridad** → activar
   protocolo de incidentes de seguridad y notificar al líder de seguridad.
4. **Si fue por bug en la aplicación** → documentar en el sistema de tickets
   y corregir el bug (no "corregir" la cadena manualmente).

---

## 6. Disco lleno

**Síntoma:** Contenedor no puede escribir; errores "No space left on device".

### Diagnóstico

```bash
# Espacio en volúmenes Docker
docker system df -v

# Espacio en el servidor
df -h

# Top volúmenes por uso
docker system df

# Ver qué ocupa el directorio de MinIO
docker compose exec minio mc du minio/fodejas-backups/

# Ver logs de MinIO
docker compose logs --tail=20 minio | grep -iE "space|quota|disk"
```

### Acción

```bash
# Limpiar backups antiguos en MinIO (forzar limpieza)
docker compose exec backup-scheduler sh -c \
  'mc rm --recursive --force --older-than 7d minio/fodejas-backups/base/'
docker compose exec backup-scheduler sh -c \
  'mc rm --recursive --force --older-than 30d minio/fodejas-backups/wal/'

# Limpiar WAL locales (ya están en MinIO)
docker compose exec db sh -c 'rm -rf /var/lib/postgresql/wal_archive/archive_*'

# Limpiar logs Docker antiguos
docker compose exec backup-scheduler sh -c 'rm -rf /var/log/*.log'

# Si el volumen de PostgreSQL está lleno: CRÍTICO
# Verificar que WAL están en MinIO (verificar antes de limpiar)
mc ls minio/fodejas-backups/wal/ | tail -3
# Si hay WAL recientes: la data está segura, se puede limpiar el wal_archive local
```

### Verificación

```bash
df -h
# Verificar que hay espacio disponible

curl -f http://localhost:8000/readyz
```

**Escalar a P1** si PostgreSQL no puede escribir tras limpieza.

---

## 7. Lentitud extrema (performance degradada)

**Síntoma:** La aplicación responde lentamente (> 5s por request).

### Diagnóstico

```bash
# 1. ¿DB es el cuello de botella?
docker compose exec db psql -U fodejas_user -d fodejas_db -c \
  "SELECT pid, now() - query_start AS duration, state, query
   FROM pg_stat_activity WHERE state != 'idle'
   ORDER BY duration DESC LIMIT 10;"

# 2. ¿Cache hit ratio bajo?
docker compose exec db psql -U fodejas_user -d fodejas_db -c \
  "SELECT
    sum(blks_hit)*100.0 / nullif(sum(blks_hit)+sum(blks_read),0) AS cache_hit_ratio
   FROM pg_stat_database;"

# 3. ¿Prometheus metrics muestran lentitud?
curl -s http://localhost:9090/api/v1/query?query=pg_stat_database_numbackends | \
  python -m json.tool

# 4. Buscar queries lentas en logs
docker compose logs --tail=500 app | grep -E "slow|seconds|duration" | tail -20

# 5. ¿Logs JSON con request_id para correlar? (producción)
docker compose logs --tail=100 app | python -c "
import sys, json
for line in sys.stdin:
    try:
        d = json.loads(line)
        if d.get('level') == 'WARNING':
            print(d.get('request_id',''), d.get('message',''))
    except:
        pass
"
```

### Acción

```bash
# Queries bloqueantes: terminar la más antigua
# (reemplazar <pid> con el valor real)
docker compose exec db psql -U fodejas_user -d fodejas_db -c \
  "SELECT pg_terminate_backend(<pid>);"

# Redis: verificar que no está sin memoria
docker compose exec redis redis-cli info memory

# Si el problema es recurrente: escalar a P2 con evidencia de queries lentas.
```

---

## 8. Configuración de firma electrónica incorrecta

**Síntoma:** `check_signer_config` falla en producción/staging.

### Diagnóstico y acción

```bash
# Verificar valor actual
docker compose exec app python manage.py check_signer_config

# Error típico en producción: "SIGNATURE_PROVIDER=mock is NOT allowed"
# Solución: cambiar a local en el compose
#   Editar docker-compose.production.yml y agregar:
#   - SIGNATURE_PROVIDER=local

# Si ya está en 'local' pero sigue fallando:
#   → Verificar que la variable está efectivamente en el contenedor:
docker compose exec app env | grep SIGNATURE_PROVIDER
```

---

## 9. Cuándo escalar

| Situación | Severidad | Destinatario |
|---|---|---|
| App no disponible en producción > 15 min | P1 | Líder técnico + equipo |
| Base de datos no levanta > 15 min | P1 | Líder técnico |
| Cadena de auditoría rota (cualquier causa) | P1 | Líder técnico |
| Backup no disponible > 1 hora | P2 | Líder técnico |
| Redis no levanta > 10 min | P2 | Operador senior |
| Breach de seguridad sospecha | P1 | Líder técnico + Seguridad |
| Decisión de restore de producción | P1 | Líder técnico + Dirección |

---

## 10. Contactos de emergencia

| Rol | Responsabilidad | Canal |
|---|---|---|
| Operador on-call | Primera respuesta | Ticket / Slack ops |
| Líder técnico | Decisiones técnicas | Canal privado |
| Dirección FODEJAS | Decisiones de negocio (restore, SLA) | Teléfono institucional |

> Los canales específicos se configuran en el onboarding del equipo.
> Este documento no contiene números de contacto por seguridad.

---

Anterior: [`02-backup-disaster-recovery.md`](02-backup-disaster-recovery.md)
|
Siguiente: [`04-monitoring-alerts.md`](04-monitoring-alerts.md)
