# Gaps Conocidos — FODEJAS

> Registro honesto de limitaciones, alertas rotas y defectos operativos.
> Este documento se actualiza por PR cuando se descubre o resuelve un gap.
> Última actualización: `feat/CHG-507-multilang`.

---

## Tabla resumen

| # | Gap | Severidad | ¿Bloqueante go-live? | Estado |
|---|---|---|---|---|
| 1 | FileField/MEDIA no configurado — PDFs y anexos no servibles | Alta | ✅ Sí | Pendiente |
| 2 | `backup-exporter` no existía — alertas de backup no confiables. **CERRADO (chore/ops-hardening):** servicio node-exporter añadido compartiendo el volumen `backup_metrics`; lógica invertida de `BackupJobFailed` corregida (== 0 → == 1). | Alta | No | Cerrado |
| 3 | `pg_stat_statements` no habilitado — `PostgresSlowQueries` siempre null. **CERRADO (chore/ops-hardening):** preload + init script. Caveat: en volúmenes existentes correr `CREATE EXTENSION IF NOT EXISTS pg_stat_statements;` y reiniciar db. | Media | No | Cerrado (con caveat initdb) |
| 4 | `backup_verify.sh` no ejecuta `pg_restore` — restore sin probar | **Crítica** | ✅ **Sí** | **PENDIENTE — primera ejecución obligatoria** |
| 5 | Workflows `deploy-staging.yml` y `deploy-production.yml` son placeholders | Alta | No | Pendiente |
| 6 | MinIO en prod sin política de versionado/ciclo de vida. **CERRADO (chore/ops-hardening):** `docker/minio-init/lifecycle.sh` con versioning + no-current 90d + uploads incompletos 30d. | Alta | ✅ Sí | Cerrado |
| 7 | Sin Grafana en compose — solo Prometheus disponible | Media | No | Pendiente |
| 8 | Sin SLOs definidos formalmente | Media | No | Pendiente (propuestos en [`04-monitoring-alerts.md`](04-monitoring-alerts.md)) |
| 9 | Email no implementado — notificaciones solo in-app | Baja | No | Por diseño |
| 10 | `collectstatic`/`compilemessages` no en CI. **CERRADO (chore/ops-hardening):** ambos pasos añadidos al job test (traducciones: validación only, .mo regenerados NO se commitean). | Media | No | Cerrado |

---

## Gap #1 — FileField/MEDIA no configurado

**Descripción:** Los campos `FileField` en los modelos de la aplicación
(GestiónDocumento, anexos de convocatoria, etc.) no tienen un storage backend
S3/MinIO configurado. Llamar `.url` en un FileField produce URLs malformadas
o rutas locales no servibles desde el contenedor.

**Evidencia:**
- No hay configuración `DEFAULT_FILE_STORAGE` ni `MEDIA_URL` en
  `config/settings.py`.
- Los archivos se guardan en el sistema de archivos local del contenedor
  (`/app/media/`) que se pierde al reiniciar.
- `boto3` / `storages.backends` no están configurados como backend para
  FileFields.

**Impacto operativo:**
- Los PDFs del portal de transparencia y los anexos de convocatorias
  **no son accesibles** desde el navegador.
- Imposible subir documentos oficiales firmados.
- Pérdida de documentos al reiniciar el contenedor.

**Estado:** Pendiente — requiere decisión de infraestructura:
1. Configurar `storages.backends.s3boto3.S3Boto3Storage` como storage backend
   con el bucket MinIO existente (`fodejas-media`).
2. Definir `MEDIA_URL` y `DEFAULT_FILE_STORAGE` en settings.
3. O usar una vista `serve` de Django para servir archivos locales
   (menos recomendado para producción).

**Responsable:** Infraestructura / Líder técnico.

---

## Gap #2 — `backup-exporter` no existe

**Descripción:** El contenedor `backup-exporter:9100` referenced en
`docker/prometheus/prometheus.yml` no existe en `docker-compose.yml`.
Las alertas `BackupJobFailed` y `BackupNotRunning` leen de una métrica
que Prometheus nunca puede obtener porque no hay target.

**Evidencia:**
- `docker/prometheus/prometheus.yml`: `targets: ['backup-exporter:9100']`
- `docker-compose.yml`: No existe servicio `backup-exporter`.
- `docker/backup-metrics/backup-metrics.sh`: escribe en textfile collector
  dentro de `fodejas_backup_scheduler`.

**Impacto operativo:**
- Las alertas de backup siempre son false positives o false negatives.
- El operador debe verificar manualmente con `mc ls minio/fodejas-backups/`.

**Fix conocido:** Crear servicio `backup-exporter` en compose usando
`prom/node-exporter` con `--collector.textfile.directory` pointing al
volumen `backup_metrics`, y ajustar el `scrape_config` de Prometheus para
apuntar al nuevo target.

**Estado:** Pendiente.
**Referencia:** [`04-monitoring-alerts.md`](04-monitoring-alerts.md) §4.

---

## Gap #3 — `PostgresSlowQueries` siempre null

**Descripción:** La extensión `pg_stat_statements` **no está habilitada**
en PostgreSQL (`docker/postgres.conf`). La expresión de la alerta
`rate(pg_stat_statements_mean_exec_time_ms[5m])` siempre devuelve `NaN`.

**Evidencia:**
- `docker/postgres.conf` líneas ~52-54: No existe la línea
  `shared_preload_libraries = 'pg_stat_statements'`.
- `docker compose exec db psql ... -c "\\dx pg_stat_statements"`:
  `pg_stat_statements` no existe.
- La alerta `PostgresSlowQueries` nunca dispara, pero tampoco detecta queries
  lentas reales.

**Impacto operativo:** No hay visibilidad sobre queries que degradan el
rendimiento. Un query que tarda 30s no genera ninguna alerta.

**Fix:** Agregar en `docker/postgres.conf`:
```ini
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
```
Luego `docker compose restart db` y verificar con:
```sql
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC LIMIT 10;
```

**Estado:** Pendiente.
**Referencia:** [`04-monitoring-alerts.md`](04-monitoring-alerts.md) §4.

---

## Gap #4 — Restore nunca probado (CRÍTICO — BLOQUEANTE)

**Descripción:** `scripts/backup/backup_verify.sh` **no ejecuta `pg_restore`**;
solo descarga el backup más reciente, extrae los TAR, verifica presencia
de archivos WAL y limpia. El procedimiento de restore completo (incluyendo
extracción, aplicación de WAL, y verificación de datos) **nunca se ha
probado ni en staging ni en producción**.

**Evidencia:**
- `scripts/backup/backup_verify.sh` líneas ~35-50: Solo `tar -xzf` y verificación
  de presencia de archivos. No hay `pg_restore`.
- `roadmap.md:207`: "un procedimiento de restore probado en staging" —
  **requisito no satisfecho**.
- No existe registro de prueba de restore en el repositorio.

**Impacto operativo:**
- **Si ocurre un desastre real, el equipo no sabe con certeza si el restore
  funciona.** Puede haber sorpresas (permissões, encoding, extensiones
  faltantes, etc.) en el momento más crítico.
- La garantía de recoverabilidad es cero hasta que se pruebe.

**ACCIÓN OBLIGATORIA antes de go-live:**
1. Ejecutar el protocolo de prueba de restore en staging
   (documentado en [`02-backup-disaster-recovery.md`](02-backup-disaster-recovery.md) §6).
2. Registrar el resultado (checklist firmado) en `docs/ops/execution-logs/`.
3. Solo tras prueba exitosa: marcar este gap como "resuelto".

**Estado:** Pendiente — **primera ejecución obligatoria antes de go-live**.

---

## Gap #5 — Deploy workflows son placeholders

**Descripción:** Los workflows GitHub Actions `deploy-staging.yml` y
`deploy-production.yml` contienen solo `echo` y no automatizan ningún
despliegue real. No hay SSH, no hay `docker compose pull`, no hay
integración con el servidor de producción.

**Evidencia:**
- `.github/workflows/deploy-staging.yml`: Solo `echo "Deploying..."` y notas.
- `.github/workflows/deploy-production.yml`: Solo `echo "Deploying..."` y notas.

**Impacto operativo:**
- Todo deploy a staging y producción es **manual** usando el runbook
  en [`01-deploy-runbook.md`](01-deploy-runbook.md).
- El runbook es la fuente de verdad operativa hasta que se implementen
  los workflows de deploy.

**Fix:** Implementar workflows con:
- SSH al servidor destino, o
- Integración con Kubernetes/Helm, o
- Integración con un PaaS (Railway, Render, etc.)

**Estado:** Pendiente. Runbook manual documentado en [`01-deploy-runbook.md`](01-deploy-runbook.md).
**Responsable:** Infraestructura.

---

## Gap #6 — MinIO sin política de versionado/ciclo de vida definida

**Descripción:** El bucket `fodejas-backups` en MinIO no tiene una política
de ciclo de vida (expiración de objetos, transición a storage más frío).
El cleanup de archivos antiguos se hace con `mc rm --older-than` en los
scripts, pero no hay protección contra fallo del script o crecimiento
descontrolado.

**Evidencia:**
- `docker/postgres.conf` y scripts: retention 7d (base) y 30d (WAL) solo
  en `base_backup.sh` y `wal_archive.sh` vía `mc rm --older-than`.
- No hay bucket lifecycle policy configurada en MinIO.
- `roadmap.md` línea ~211: requisito de versionado/cifrado/ciclo de vida
  para el bucket de anexos no satisfecho (además del bucket de backups).

**Impacto operativo:**
- Si el script de cleanup falla, el bucket crece indefinidamente.
- Los archivos de backups no están versionados (si se sobreescribe un
  backup con el mismo nombre, el anterior se pierde).

**Fix propuesto:**
```bash
# Crear política de lifecycle en MinIO
mc ilm import minio/fodejas-backups << 'EOF'
{
  "Rules": [
    {
      "ID": "base-backup-7d",
      "Status": "Enabled",
      "Filter": {"Prefix": "base/"},
      "Expiration": {"Days": 7}
    },
    {
      "ID": "wal-30d",
      "Status": "Enabled",
      "Filter": {"Prefix": "wal/"},
      "Expiration": {"Days": 30}
    }
  ]
}
EOF
```

**Estado:** Pendiente. Requiere implementación + validación en staging.
**Responsable:** Infraestructura.

---

## Gap #7 — Sin Grafana

**Descripción:** El stack de monitoreo tiene Prometheus pero no Grafana.
Las métricas de Prometheus están disponibles en `http://localhost:9090`
pero sin dashboards gráficos preconfigurados.

**Evidencia:**
- `docker-compose.yml`: No existe servicio `grafana`.
- `docker/grafana/` directorio existe (probablemente para configuración
  futura) pero está vacío.

**Impacto operativo:**
- Visualización de métricas requiere acceso directo a Prometheus (no ideal
  para operadores no técnicos).
- No hay dashboards de SLO, uptime, o tendencias de rendimiento.

**Fix:** Agregar `grafana` al compose con persistencia y datasource
Preconfigurado hacia Prometheus. Crear dashboards para:
- Disponibilidad (uptime ratio).
- Latencia (percentiles).
- Backups (éxito/fallo histórico).
- Conexiones PgBouncer.
- Tareas Celery.

**Estado:** Pendiente.
**Prioridad:** Baja para MVP — mejorar visibilidad pero no crítico.

---

## Gap #8 — Sin SLOs definidos formalmente

**Descripción:** Los valores de SLO en [`04-monitoring-alerts.md`](04-monitoring-alerts.md)
son **propuestos** (disponibilidad 99%, latencia p95 < 2s). No existe
documento de SLO aprobado por la institución.

**Evidencia:**
- No hay archivo `slos.md` ni equivalente en el repositorio.
- Los valores propuestos no tienen validación institucional.

**Impacto operativo:**
- Sin SLOs aprobados no hay forma objetiva de medir si el servicio cumple
  las expectativas de la institución.
- Los errores budget no se pueden gestionar formalmente.

**Fix:** Redactar `docs/ops/slos.md` con SLOs propuestos, presentar a la
dirección de FODEJAS para aprobación, y registrar el resultado.

**Estado:** Pendiente. Propuestos en [`04-monitoring-alerts.md`](04-monitoring-alerts.md) §7.

---

## Gap #9 — Email no implementado

**Descripción:** La plataforma no envía correos electrónicos transaccionales.
Las notificaciones (nuevas convocatorias, estado de postulación, alertas
de tesorería, Habeas Data) son **solo in-app** (registro en la base de datos
y visible en la interfaz).

**Evidencia:**
- No hay configuración SMTP en `config/settings.py`.
- `roadmap.md:176`: INF-009 (email transaccional) está **ELIMINADO** del roadmap.
- Las notificaciones CAP-019 son "internas".

**Impacto operativo:**
- Los beneficiarios no reciben correos de notificación.
- Para comunicar estados de postulación es necesario contacto manual
  o integración futura con un sistema de notificaciones externo.

**Por diseño** — no es un gap a cerrar en esta fase. Documentado aquí
para expectativa de los operadores.

---

## Gap #10 — `collectstatic` y `compilemessages` ausentes en CI

**Descripción:** El workflow `ci.yml` no ejecuta `python manage.py collectstatic`
ni `python manage.py compilemessages` como paso de verificación.
Esto significa que:
- Archivos estáticos mal configurados no se detectan en CI.
- Traducciones con errores de formato no se detectan en CI.

**Evidencia:**
- `.github/workflows/ci.yml`: No tiene paso de `collectstatic` ni `compilemessages`.
- `roadmap.md` línea ~585: no menciona estas verificaciones en CI.

**Impacto operativo:**
- Un deploy puede completar con archivos estáticos faltantes o traducciones
  rotas sin que CI lo detecte.
- El operador descubre el problema post-deploy.

**Fix propuesto** (agregar a `ci.yml`):
```yaml
- name: Collect static files
  run: python manage.py collectstatic --noinput --verbosity 2

- name: Compile translations
  run: python manage.py compilemessages
```

**Estado:** Pendiente.
**Responsable:** DevOps / Líder técnico.

---

## Reglas de actualización de este documento

1. **Nuevo gap descubierto** → agregar entrada con evidencia concreta
   (path:line, output de comando, screenshot si aplica).
2. **Gap resuelto** → marcar estado como "Resuelto (YYYY-MM-DD)"
   y agregar link al commit/PR que lo cerró.
3. **Gap que se convierte en bloqueante** → actualizar severidad y
   marcar "¿Bloqueante go-live?" a "Sí".
4. **Este documento se actualiza por PR** — no modificar en rama `main`
   directamente.

---

Anterior: [`04-monitoring-alerts.md`](04-monitoring-alerts.md)
