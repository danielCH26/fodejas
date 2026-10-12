# Plan de Recuperación ante Desastres (DRP) — FODEJAS

> Arquitectura de backups, procedimientos de restore y recuperación.
> Referencia: roadmap.md INF-011.
>
> ⚠ **POLÍTICA NO APROBADA — VALORES PROPUESTOS:**
> Los valores de RTO y RPO en este documento son **propuestos**.
> Requieren validación y aprobación institucional antes de constituir
> política oficial. Marcar como `PROPUESTO` en todas las referencias.

---

## 1. Arquitectura de backups

### 1.1 Componentes y flujo

```
PostgreSQL 16 (fodejas_db)
  ├── WAL segments ──(archive_command)──► /var/lib/postgresql/wal_archive/
  │                                           └── wal_archive.sh (cron */15)
  │                                                └── mc cp ──► MinIO s3://fodejas-backups/wal/
  └── pg_basebackup (cron 02:00)
            └── base_backup.sh
                  └── mc cp ──► MinIO s3://fodejas-backups/base/

Backup scheduler (fodejas_backup_scheduler, alpine + dcron)
  ├── backup_verify.sh  (cron 03:00) ──► Verifica presencia de archivos en MinIO
  └── backup-metrics.sh (cron */5)  ──► Actualiza Prometheus textfile collector
```

### 1.2 Detalle de scripts

| Script | Ubicación | Schedule | Qué hace | Qué NO hace |
|---|---|---|---|---|
| `base_backup.sh` | `scripts/backup/base_backup.sh` | 02:00 daily | `pg_basebackup -Ft -z` → MinIO `base/` | No elimina tablas ni hace vacuum |
| `wal_archive.sh` | `scripts/backup/wal_archive.sh` | `*/15 * * * *` | Copia WAL desde `/var/lib/postgresql/wal_archive/` → MinIO `wal/` | No archiva transacciones individuales |
| `backup_verify.sh` | `scripts/backup/backup_verify.sh` | 03:00 daily | Descarga backup más reciente, verifica presencia de archivos TAR y WAL | **NO ejecuta `pg_restore` ni prueba restore real** |
| `backup-metrics.sh` | `docker/backup-metrics/backup-metrics.sh` | `*/5 * * * *` | Actualiza `backup_metrics.prom` (status, timestamp, nombres) | No modifica la BD ni los backups |

### 1.3 Retenciones

| Bucket en MinIO | Contenido | Retención |
|---|---|---|
| `fodejas-backups/base/` | Base backups (tar + tar.z) | **7 días** (`mc rm --older-than 7d`) |
| `fodejas-backups/wal/` | WAL archives | **30 días** (`mc rm --older-than 30d`) |

### 1.4 Configuración PostgreSQL relevante

```ini
# docker/postgres.conf
wal_level         = replica       # Habilita archive_mode y wal_senders
max_wal_senders   = 3
archive_mode      = on
archive_command   = 'test ! -f /var/lib/postgresql/wal_archive/%f && cp %p /var/lib/postgresql/wal_archive/%f'
archive_timeout   = 300           # Force archive cada 5 min si no hay actividad
hot_standby       = on
```

### 1.5 Contenedor backup-scheduler

```
fodejas_backup_scheduler  (alpine:3.19 + dcron + mc + bash)
  volumes:
    ../scripts/backup:/scripts/backup:ro
    ./backup-metrics/crontab:/etc/crontabs/root:ro
    backup_metrics:/var/lib/node_exporter/textfile_collector
```

**Crontab real** (`docker/backup-metrics/crontab`):
```cron
0 2 * * * /scripts/backup/base_backup.sh >> /var/log/backup.log 2>&1
*/15 * * * * /scripts/backup/wal_archive.sh >> /var/log/wal_archive.log 2>&1
0 3 * * * /scripts/backup/backup_verify.sh >> /var/log/backup_verify.log 2>&1
*/5 * * * * /scripts/backup-metrics/backup-metrics.sh >> /var/log/backup_metrics.log 2>&1
```

---

## 2. Métricas Prometheus (estado real)

El `backup-metrics.sh` escribe en el textfile collector de Prometheus
(`backup_metrics.prom`). Las métricas generadas son:

| Métrica | Tipo | Significado |
|---|---|---|
| `backup_job_last_run_status` | gauge | `0` = éxito, `1` = fallo |
| `backup_job_last_success_timestamp` | gauge | Unix timestamp del último backup exitoso |
| `backup_latest_base_backup_name` | gauge | Constante `1` (nombre real no exposeable como gauge) |
| `backup_latest_wal_archive_name` | gauge | Constante `1` (nombre real no exposeable como gauge) |

⚠ **GAP documentado:** No existe el contenedor `backup-exporter:9100`.
Prometheus está configurado para hacer scrape de ese objetivo
(`docker/prometheus/prometheus.yml` job `backup-jobs`), pero el contenedor
no existe. Las alertas `BackupJobFailed` y `BackupNotRunning`
(**siempre disparan false positives**). Ver [`05-known-gaps.md`](05-known-gaps.md) Gap #2.

---

## 3. RTO y RPO — VALORES PROPUESTOS

| Métrica | Valor propuesto | Condición | Notas |
|---|---|---|---|
| **RPO** | ≤ 15 minutos | Con WAL archive activo (cada 15 min) | La pérdida máxima de datos es un WAL segment (~5 min idle + copia) |
| **RPO** | ≤ 24 horas | Si el restore es **solo** desde base backup (sin WAL) | Supone que WAL se perdió o no se puede aplicar |
| **RTO** | ≤ 4 horas | Desde declaración de incidente hasta servicio disponible | Incluye diagnóstico, decisión de restore, ejecución, verificación |

> **Valores propuestos, pendientes de aprobación institucional.**
> Estos NO son política de recuperación aprobada. Se requiere revisión
> por el equipo directivo y el área de sistemas antes de go-live.

### Validación de RPO en curso

- Para cumplir RPO ≤ 15 min, verificar que:
  1. `wal_archive.sh` se ejecuta sin errores (`docker compose logs backup-scheduler | grep wal_archive`).
  2. Los archivos WAL aparecen en MinIO `fodejas-backups/wal/` dentro de los 15 min.
  3. `backup_verify.sh` confirma la presencia de WAL reciente.

---

## 4. Procedimiento de RESTORE completo

### 4.1 Restaurar desde base backup (punto en el tiempo arbitrario)

**Supuestos:**
- PostgreSQL se ejecuta en el contenedor `fodejas_db`.
- Los backups están en MinIO `s3://fodejas-backups/base/`.
- El bucket MinIO es accesible desde el scheduler.

```bash
# --- PASO 1: Detener la aplicación (no escribir durante restore) ---
docker compose stop app celery-worker celery-beat

# --- PASO 2: Identificar el backup más reciente ---
# Desde el contenedor backup-scheduler o cualquier máquina con mc + credenciales:
mc ls minio/fodejas-backups/base/
# Anotar el directorio del backup más reciente, ej: base_backup_20241201_020000/

# --- PASO 3: Descargar el backup ---
BACKUP_NAME="base_backup_20241201_020000"   # <-- ajustar
mkdir -p /tmp/restore_${BACKUP_NAME}
mc cp --recursive "minio/fodejas-backups/base/${BACKUP_NAME}/" /tmp/restore_${BACKUP_NAME}/

# --- PASO 4: Detener PostgreSQL ---
docker compose stop db

# --- PASO 5: Respaldar el directorio de datos actual (por seguridad) ---
mv /var/lib/docker/volumes/fodejas_postgres_data/_data \
   /var/lib/docker/volumes/fodejas_postgres_data/_data_old_$(date +%Y%m%d%H%M%S)

# --- PASO 6: Crear directorio de datos limpio ---
mkdir -p /var/lib/docker/volumes/fodejas_postgres_data/_data

# --- PASO 7: Extraer el base backup ---
cd /tmp/restore_${BACKUP_NAME}
tar -xzf base.tar.gz -C /var/lib/docker/volumes/fodejas_postgres_data/_data/
tar -xzf pg_wal.tar.gz -C /var/lib/docker/volumes/fodejas_postgres_data/_data/pg_wal/
# pg_basebackup -Ft -z crea: base.tar.gz, pg_wal.tar.gz (y opcionalmente tablespace.tar.gz)

# --- PASO 8: Ajustar propietario ---
chown -R postgres:postgres /var/lib/docker/volumes/fodejas_postgres_data/_data/
chmod 0700 /var/lib/docker/volumes/fodejas_postgres_data/_data/

# --- PASO 9: Levantar PostgreSQL ---
docker compose up -d db
docker compose logs -f db | grep -E "database system is ready|recovery"

# --- PASO 10: Verificar que PostgreSQL responde ---
docker compose exec db pg_isready -U fodejas_user -d fodejas_db

# --- PASO 11: Verificar la base de datos restaurada ---
docker compose exec db psql -U fodejas_user -d fodejas_db -c "SELECT count(*) FROM django_migrations;"

# --- PASO 12: Levantar la aplicación ---
docker compose up -d app celery-worker celery-beat

# --- PASO 13: Verificar readiness ---
curl -f http://localhost:8000/readyz
```

### 4.2 Restaurar a un punto en el tiempo (PITR) con WAL

Para restaurar a un momento específico posterior al base backup:

```bash
# 1. Ejecutar pasos 1-8 de §4.1

# 2. Crear archivo recovery.conf (PostgreSQL 12-15: usa postgresql.conf + postgresql.auto.conf)
cat > /var/lib/docker/volumes/fodejas_postgres_data/_data/postgresql.auto.conf << 'EOF'
restore_command = 'mc cat minio/fodejas-backups/wal/%f > %p'
recovery_target_time = '2024-12-01 14:30:00-05'   # <-- ajustar UTC-5 para Colombia
recovery_target_action = 'promote'
EOF

# 3. Crear archivo de señal de recuperación
touch /var/lib/docker/volumes/fodejas_postgres_data/_data/recovery.signal

# 4. Continuar con pasos 9-13
```

> **Nota:** El archivo `recovery.signal` (no `recovery.conf`) se usa en
> PostgreSQL 12+. La presencia de este archivo indica a PostgreSQL que
> debe operar en modo de recuperación.

### 4.3 Restaurar solo archivos WAL (si el base backup está corrupto)

Si el base backup está dañado pero los WAL están intactos:

```bash
# 1. Reconstruir desde WAL play-forward
#    Requiere un base backup anterior funcional o reconstruir desde cero
#    Consultar con el líder técnico antes de ejecutar.
```

---

## 5. Verificación post-restore

```bash
# a) Readiness OK
curl -f http://localhost:8000/readyz

# b) Verificar conteo de registros críticos (ejemplo)
docker compose exec app python manage.py shell -c "
from apps.convocatories.models import Convocatoria
from apps.applications.models import Application
print(f'Convocatorias: {Convocatoria.objects.count()}')
print(f'Aplicaciones:  {Application.objects.count()}')
"

# c) Cadena de auditoría intacta
docker compose exec app python manage.py shell -c \
  "from apps.audit.services import verify_chain; r=verify_chain(); print(f'Cadena: {\"OK\" if r[\"is_valid\"] else \"ROTA en \"+str(r[\"break_point\"])}')"

# d) Logs sin errores recientes
docker compose logs --since=10m app | grep -iE "error|exception|traceback" | head -20
```

---

## 6. Protocolo de prueba de restore en staging

> ⚠ **ACCIÓN PENDIENTE — BLOQUEANTE PARA GO-LIVE**
>
> La prueba de restore **nunca se ha ejecutado** en staging.
> `backup_verify.sh` no ejecuta `pg_restore`; solo verifica presencia
> de archivos. El requisito en `roadmap.md:207` ("restore probado en staging")
> **no está satisfecho**.
>
> Esta prueba es **bloqueante** antes de cualquier despliegue a producción.

### Frecuencia propuesta

- **Primera ejecución:** Antes de go-live (obligatorio).
- **Mensual:** Repetir el protocolo completo.
- **Tras cualquier cambio en la arquitectura de backups.**

### Checklist de prueba de restore en staging

```markdown
## Prueba de Restore — Staging
Fecha: _______________
Ejecutor: _______________
Incidente relacionado (si aplica): _______________

### Pre-condiciones
- [ ] Backup más reciente disponible en MinIO (verificar con mc ls)
- [ ] Base de datos staging tiene datos de prueba recientes
- [ ] Notificar al equipo que staging estará fuera de línea ~15 min

### Ejecución
- [ ] Registrar conteos actuales de tablas (migrations, users, applications)
- [ ] Detener servicios app/celery
- [ ] Ejecutar restore de base backup (procedimiento §4.1)
- [ ] Aplicar WAL hasta punto de prueba (opcional)
- [ ] Verificar conteos de tablas post-restore vs pre-restore
- [ ] Verificar /readyz → 200 OK
- [ ] Verificar login y flujo básico en staging
- [ ] Verificar cadena de auditoría con verify_chain()

### Resultado
- [ ] Restore exitoso: __SI / NO__
- [ ] Pérdida de datos tolerable: __SI / NO__
- [ ] Tiempo total del restore: ___ minutos
- [ ] Anomalías observadas: _______________

### Firma de aprobación
Líder técnico: _______________ Fecha: _______________
```

**Registro de ejecuciones:** Guardar el checklist firmado en el directorio
`docs/ops/execution-logs/` del repositorio (archivo por ejecución).

---

## 7. Escenarios de desastre

### 7.1 Pérdida total de la base de datos

**Síntoma:** Contenedor `fodejas_db` destruido o volumen corrupto.
**RPO real:** Último base backup disponible (hasta 24h si el daily falló).
**RTO real:** ~30-60 min (restore de base backup).

1. Ejecutar §4 pasos 1-13.
2. Si hay WAL disponibles y se necesita punto reciente, usar PITR (§4.2).
3. Verificar cadena de auditoría post-restore.

### 7.2 Pérdida del bucket MinIO (backups y medios)

**Síntoma:** Bucket `fodejas-backups` eliminado o inaccesible.

1. Verificar acceso a MinIO: `mc ls minio/`
2. Si el bucket se eliminó accidentalmente:
   ```bash
   mc mb minio/fodejas-backups
   mc anonymous set download minio/fodejas-backups  # si aplica
   ```
3. **Restaurar desde réplicas externas** si existen (n/a en versión actual — GAP #6).
4. **Reactivar jobs de backup inmediatamente** y hacer un base backup manual:
   ```bash
   docker compose exec backup-scheduler /scripts/backup/base_backup.sh
   ```
5. Verificar en MinIO que aparecen los nuevos archivos en `base/` y `wal/`.

### 7.3 Corrupción lógica de datos (borrado accidental de registros)

**Síntoma:** Registros eliminados/modificados sin respaldo en aplicación.

1. **NO modificar nada** hasta que el líder técnico evalúe.
2. Identificar el punto en el tiempo antes de la corrupción.
3. Si hay WAL continuity: restaurar a ese punto con PITR (§4.2).
4. Si no hay WAL continuity: restaurar desde base backup y reconstruir
   los registros posteriores manualmente (involucra al equipo de producto).
5. Documentar el incidente en el log de auditoría y en el sistema de tickets.

### 7.4 Fallo de disco en servidor

**Síntoma:** Volumen Docker lleno o disco corrupto.

1. Verificar espacio: `df -h`
2. Si el volumen `postgres_data` está lleno:
   - Limpiar WAL locales: `rm -rf /var/lib/postgresql/wal_archive/*`
   - Los WAL ya están en MinIO (archive_command), no se pierde data.
3. Evaluar necesidad deexpansion de volumen antes de continuar.
4. Continuar con restore si los datos están comprometidos.

---

## 8. Roles y responsables

| Acción | Responsable | Rol requerido |
|---|---|---|
| Ejecutar restore | Operador de sistemas | Superusuario + acceso SSH al servidor |
| Autorizar restore productivo | Líder técnico | Superusuario |
| Ejecutar backup manual | Operador | Acceso al contenedor backup-scheduler |
| Verificar integridad de cadena post-restore | Operador | Acceso shell Django |
| Registrar prueba de restore | Operador | — |
| Monitorear métricas de backup | Operador | Acceso Prometheus |

---

Anterior: [`01-deploy-runbook.md`](01-deploy-runbook.md)
|
Siguiente: [`03-incident-response.md`](03-incident-response.md)
