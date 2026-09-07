# Schemas de datos legacy (CHG-099)

> Documento vivo. Referencia: `openspec/changes/CHG-099-migration/`.

Estos son los **headers esperados** de los 5 archivos CSV que
`migrate_legacy_data` consume. Todos los archivos DEBEN tener
exactamente estas columnas (orden libre, pero las columnas DEBEN
existir). Cualquier columna faltante o extra produce un error de
validación y el comando aborta.

> ⚠️ **REGLA DE ORO**: estos schemas describen los DATOS ANONIMIZADOS
> que el repo acepta. Los archivos reales con PII NUNCA entran al
> repo. La anonimización se hace ANTES de la migración, fuera del
> control de versiones.

---

## 1. `convocatorias.csv` → `apps.convocatories.models.Convocatory`

| Columna | Tipo | Nullable | Notas |
|---------|------|----------|-------|
| `codigo` | str | NO | Clave natural. Único dentro del archivo. Ej: `CONV-001-2025`. |
| `nombre` | str | NO | Anonimizado: `sha256(original + salt)[:12]`. |
| `tipo` | str | NO | `cerrada` o `abierta`. |
| `periodo` | str | NO | Ej: `2025-1`. |
| `estado` | str | NO | `BORRADOR`, `PUBLICADA`, `EN_CALIFICACION`, `DEFINITIVA`, `CERRADA`. |
| `fecha_apertura` | date | SÍ | ISO 8601 (`YYYY-MM-DD`). |
| `fecha_cierre` | date | SÍ | |
| `fecha_publicacion_preliminar` | datetime | SÍ | ISO 8601 con hora. |
| `fecha_publicacion_definitiva` | datetime | SÍ | |
| `monto_semestre_smlmv` | decimal | NO | SMLMV del semestre. |
| `duracion_maxima_semestres` | int | NO | ≥ 0. |
| `cupo_total` | int | NO | ≥ 0. |
| `modalidad_codigo` | str | SÍ | FK a `core.ModalidadApoyo.codigo`. Si falta, se omite. |

---

## 2. `solicitudes.csv` → `apps.applications.models.Solicitud`

| Columna | Tipo | Nullable | Notas |
|---------|------|----------|-------|
| `radicado` | str | NO | Clave natural. Único dentro del archivo. Formato `RAD-YYYY-NNN`. |
| `convocatoria_codigo` | str | NO | FK a `convocatorias.csv:codigo`. |
| `aspirante_documento_hash` | str | NO | `sha256(documento + salt)[:12]`. |
| `estado` | str | NO | `BORRADOR`, `RADICADA`, `EN_VERIFICACION`, `VERIFICADA`, `RECHAZADA`. |
| `radicado_en` | datetime | NO | Cuándo se radicó. |
| `datos_academicos_json` | str (JSON) | SÍ | Anonimizado: el JSON se sanitiza recursivamente. |
| `datos_socioeconomicos_json` | str (JSON) | SÍ | Anonimizado. |
| `datos_personales_json` | str (JSON) | SÍ | Anonimizado. |

---

## 3. `usuarios_legacy.csv` → `apps.accounts.models.CustomUser`

| Columna | Tipo | Nullable | Notas |
|---------|------|----------|-------|
| `documento_hash` | str | NO | Clave natural. `sha256(documento + salt)[:12]`. |
| `email_hash` | str | NO | `sha256(email + salt)[:12]`. Único. |
| `role_codes` | str | NO | Pipe-separated. Ej: `R-ASPIRANTE|R-CT`. |
| `is_active` | bool | NO | Default True. |

NO se persisten nombre, apellido, email raw ni teléfono. La
identidad operativa es el par `(documento_hash, email_hash)`.

---

## 4. `actos_legacy.csv` → `apps.governance.models.ActoAdministrativo`

| Columna | Tipo | Nullable | Notas |
|---------|------|----------|-------|
| `numero` | str | NO | Clave natural. Formato `FODEJAS-{TIPO}-{YYYY}-{NNNNN}`. |
| `tipo` | str | NO | `RESOLUCION`, `ACTA`, `MODIFICATORIO`, `CERTIFICACION`. |
| `fecha_expedicion` | date | NO | |
| `fecha_publicacion` | datetime | SÍ | |
| `asunto` | str | NO | Anonimizado: no debe contener nombres propios. Si los contiene, el validador rechaza. |
| `considerandos_json` | str (JSON) | NO | Anonimizado. |
| `resolutivo` | str | NO | Anonimizado. |
| `convocatoria_codigo` | str | SÍ | FK opcional. |
| `firmantes_json` | str (JSON) | NO | Lista de strings (anonimizados). |
| `estado` | str | NO | `BORRADOR`, `FIRMADO`, `PUBLICADO`, `ANULADO`. Para migración, será siempre `PUBLICADO` o `ANULADO`. |

---

## 5. `listados_legacy.csv` → `apps.governance.models.ListadoDefinitivo`

| Columna | Tipo | Nullable | Notas |
|---------|------|----------|-------|
| `convocatoria_codigo` | str | NO | Clave natural (un ListadoDefinitivo por Convocatory). FK. |
| `ranking_json` | str (JSON) | NO | Lista de `{"rank": int, "radicado": str, "puntaje_total": decimal}`. Anonimizada: solo radicados (ya hash-safe) y puntajes. |
| `fecha_publicacion` | datetime | NO | |
| `acto_numero` | str | NO | FK a `actos_legacy.csv:numero`. |

---

## Orden de carga

El comando procesa los archivos en este orden para satisfacer FKs:

1. `convocatorias.csv` (sin FKs)
2. `usuarios_legacy.csv` (sin FKs)
3. `solicitudes.csv` (FK a Convocatory + CustomUser)
4. `actos_legacy.csv` (FK opcional a Convocatory)
5. `listados_legacy.csv` (FK a Convocatory + ActoAdministrativo)

---

## Validación de PII crudo

Cualquier valor en columnas anonimizadas que matchee las siguientes
regex produce abort inmediato:

- Email: `^[^@]+@[^@]+\.[^@]+$` (excepto `anon-test-...` que es el
  prefijo de las factories)
- Documento: `^\d{7,10}$`
- Teléfono colombiano: `^\d{10}$` o `^3\d{9}$`

Los archivos `apps/core/tests/fixtures/legacy_sample/*.csv` son el
único input válido para tests — usan el prefijo `anon-test-` para
satisfacer la validación sin PII real.
