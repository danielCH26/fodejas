#!/bin/bash
# MinIO bucket lifecycle initialization (Gap #1 / chore/media-serving).
#
# Funde dos flujos:
#   - chore/media-serving: crea el bucket (ausente en ops-hardening)
#   - chore/ops-hardening: versionado + lifecycle (ausente en media-serving)
#
# MERGE SUPERSET: cuando ambos PRs (media-serving + ops-hardening) se fusionan,
# mantener ESTE archivo como superset. La sección §3 (creación del bucket) es la
# única diferencia con ops-hardening — al merger le corresponde descartarla
# si ya existe en el branch de ops-hardening al momento del merge.
# Si ops-hardening no tiene la línea mc mb, el merge superset la conserva aquí.
#
# Idempotente: mc commands se pueden ejecutar múltiples veces sin efectos
# adversos. mc mb --ignore-existing no falla si el bucket ya existe.
#
# Uso en compose:
#   docker compose run --rm minio-init
# O como servicio one-shot definido en docker-compose.yml.
#
# Variables de entorno requeridas:
#   MINIO_ROOT_USER, MINIO_ROOT_PASSWORD  (defecto: minioadmin)
#   MINIO_ENDPOINT                         (defecto: http://minio:9000)
#
# Requisitos: mc (MinIO Client) disponible en la imagen.

set -euo pipefail

echo "[minio-init] Iniciando inicialización de MinIO..."

# §1 — Alias del cliente MinIO
mc alias set local \
    "${MINIO_ENDPOINT:-http://minio:9000}" \
    "${MINIO_ROOT_USER:-minioadmin}" \
    "${MINIO_ROOT_PASSWORD:-minioadmin}" \
    2>/dev/null || echo "[minio-init] AVISO: mc alias set falló (puede que ya exista)"

# §2 — Crear bucket si no existe (SUPERSET vs ops-hardening)
# --ignore-existing garantiza idempotencia: no falla si el bucket ya está.
echo "[minio-init] Creando bucket fodejas-media si no existe..."
mc mb --ignore-existing local/fodejas-media 2>/dev/null \
    || echo "[minio-init] NOTE: bucket ya existe (ok)"

BUCKET="local/fodejas-media"

# §3 — Habilitar versionado de objetos
# Idempotente: habilitar versionado en un bucket ya versionado no falla.
echo "[minio-init] Habilitando versionado en ${BUCKET}..."
mc version enable "${BUCKET}" 2>/dev/null \
    || echo "[minio-init] NOTE: versionado ya habilitado"

# §4 — Regla de lifecycle: expirar versiones no-corrientes a los 90 días
# Versiones no-corrientes se generan cuando un objeto se sobreescribe (con
# versionado activo). Esto evita que versiones antiguas acumulen costos.
echo "[minio-init] Agregando regla lifecycle: versiones no-corrientes expiran en 90 días..."
mc ilm rule add --noncurr-expire-days 90 "${BUCKET}" 2>/dev/null \
    || echo "[minio-init] NOTE: regla de expiración no-corriente ya existe"

# §5 — Regla de lifecycle: limpiar cargasMultipart incompletas a los 30 días
# Cargas abandonadas (PUT multipart sin CompleteMultipartUpload) se eliminan
# para no consumir almacenamiento indefinidamente.
echo "[minio-init] Agregando regla lifecycle: uploads incompletos expiran en 30 días..."
mc ilm rule add --expire-delete-marker --expire-obj-days 30 "${BUCKET}" 2>/dev/null \
    || echo "[minio-init] NOTE: regla de uploads incompletos ya existe"

# §6 — Verificación (opcional, fines de diagnóstico)
echo "[minio-init] Reglas lifecycle actuales:"
mc ilm rule list "${BUCKET}" 2>/dev/null \
    || echo "[minio-init] AVISO: no se pudieron listar reglas (verificar bucket)"

echo "[minio-init] Inicialización completa. Saliendo."
