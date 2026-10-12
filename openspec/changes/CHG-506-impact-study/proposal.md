# CHG-506 — Estudio de Impacto (CAP-027)

## Contexto

CAP-027 (Estudio de Impacto) es **P3** en el catálogo de capacidades
(`project.md §8`, línea 610). El Estudio de Impacto bianual es requerido
por `project.md §14.2` (estadísticas de impacto, Art. 20.f Manual
Operativo — referencia normativa, sin contenido inventado). La función de
"realizar estudios de impacto" corresponde al Comité Técnico
(`project.md §6.1.2`, línea 456).

CHG-503 (`openspec/changes/CHG-503-reports/proposal.md`, línea 74-76)
identificó y difirió expresamente el riesgo:

> *"agregaciones por IES/municipio dependen de campos JSON de Solicitud
> (datos_academicos) — se diferida a CHG-504/506 donde el portal las
> requiera"*

Este change materializa esa différencia.

### Hallazgos de fragilidad de datos (exploración verificada)

| Campo | Ubicación actual | Problema |
|---|---|---|
| `datos_academicos.institucion` | `CharField` libre en wizard step 2 | Texto libre sin normalización; variantes de nombre para la misma IES |
| `datos_personales.municipio` | Clave `municipio` en JSON | Código libre (`san_andres`, `providencia`, `santa_catalina`); sin FK a catálogo |
| Catálogo `MunicipioIsla` | `core.MunicipioIsla` | Vacío; sin filas sembradas |
| Catálogo `TipoIes` | `core.TipoIes` | Vacío; sin uso en este change |
| `AcademicRecord` | Sin campo retorno | No existe campo `retorno_archipelago` |

### Decisiones de producto ya tomadas

1. **Denormalización**: `Solicitud` recibe `ies_nombre` (CharField, normalizado trim en `save()`) y `municipio_origen` (FK a `core.MunicipioIsla`, null=True). Backfill mediante management command idempotente desde los blobs JSON existentes. Seed del catálogo `MunicipioIsla` con los tres municipios del Archipiélago.
2. **Retorno**: `AcademicRecord` recibe `retorno_archipelago` (BooleanField, null=True) con endpoint de anotación manual y migración.
3. **K-anonimidad**: celdas con menos de 3 beneficiarios se suprimen en los desgloses por IES y municipio (k=3), alineado con `project.md §13.2` (Ley 1581/2012 — protección de datos personales).

## Capacidades afectadas

- **CAP-027** — Estudio de Impacto (primaria)
- **CAP-011** — Seguimiento académico (nuevo campo `retorno_archipelago`)
- **CAP-023/024** — Catálogos paramétricos (seed `MunicipioIsla`)
- **CAP-020** — Reportes de Gestión (reutiliza `ReportingService`)

## Reglas de negocio afectadas

- `project.md §14.2` — Estadísticas de impacto bianuales (Art. 20.f Manual
  Operativo como referencia normativa citada; no se inventa su contenido).
- `project.md §13.2` — Protección de datos personales. La supresión k=3
  es una decisión de producto alineada con Ley 1581/2012 (project.md §13.2,
  línea 1049-1059).
- `project.md §6.1.2` — CT responsable del estudio de impacto (línea 456).
- `AGENTS.md §6` Regla 5 — pruebas en reglas monetarias (montos por
  IES/municipio son agregados monetarios).

## Cambios propuestos

### 1. Modelos y migraciones

**`apps/applications/models.py`** — `Solicitud`:

- `ies_nombre = models.CharField(max_length=255, blank=True, null=True)`:
  normalizado como `strip()` + colapso de espacios múltiples en `save()`.
  No se inventan sinónimos de IES; casefold para comparaciones.
- `municipio_origen = models.ForeignKey(
    "core.MunicipioIsla",
    on_delete=models.SET_NULL,
    null=True,
    blank=True
  )`:
  FK con `SET_NULL` para no bloquear el borrado de catálogo
  (tolerancia ante catálogos incompletos).

**`apps/academic_tracking/models.py`** — `AcademicRecord`:

- `retorno_archipelago = models.BooleanField(null=True, blank=True)`:
  true = retornó al Archipiélago, false = no retornó, null = sin anotar.

Migraciones: `makemigrations apps/applications apps/academic_tracking`.
No se altera el esquema de `LegalizationProcess` ni `DisbursementAuthorization`.

### 2. Seed del catálogo `MunicipioIsla`

**Management command** `apps/core/management/commands/seed_municipio_isla.py`:

Seeds los tres municipios del Archipiélago verificados en `project.md`
(línea 42: "Archipiélago de San Andrés, Providencia y Santa Catalina"):

| código | nombre | orden |
|---|---|---|
| `san_andres` | San Andrés | 1 |
| `providencia` | Providencia | 2 |
| `santa_catalina` | Santa Catalina | 3 |

Códigos derivados de `wizard_step_1.html:86-88` (valores del select
`municipio` en `datos_personales.municipio`: `san_andres`,
`providencia`, `santa_catalina`). El catálogo modela islas, no
municipios DANE: administrativamente Santa Catalina pertenece al
municipio de Providencia, pero el FUI la ofrece como opción propia y
el desglose del estudio la distingue. Comando idempotente
(`get_or_create`). Se justifica como management command en lugar de
data migration para facilitar re-ejecución y debugging; la idempotencia
garantiza seguridad en redeploy.

### 3. Backfill de campos de impacto

**Management command** `apps/applications/management/commands/backfill_impact_fields.py`:

Lee todas las `Solicitud` con estado que permita trazabilidad
(LEGALIZADA u otro según lo que el modelo soporte), itera con
`iterator()` + `batch_size=500` para no saturar memoria, y:

- `ies_nombre`: parsea `datos_academicos.institucion` → valor
  normalizado (`strip()` + `re.sub(r' {2,}', ' ', ...)`).
  Sin normalización de sinónimos; las variantes crudas se preservan
  en el JSON blob original.
- `municipio_origen`: busca `datos_personales.municipio` con
  `casefold()` contra `MunicipioIsla.codigo`. Sin match → asigna
  `null` e incrementa contador de "sin-match". Reporta contadores
  al final.

Bandera `--dry-run`: emite el reporte de contadores sin escribir.

Idempotencia: el comando compara valor actual con destino antes de
escribir; si ya coincide, omite la escritura.

### 4. Servicio de estudio de impacto

**`apps/reporting/services.py`** — `ReportingService.estudio_impacto(anio_inicio, anio_fin)`:

Recibe año de inicio y año de fin (ambos inclusive), valida que
`1 <= anio_fin - anio_inicio <= 4` (rango permitido 1 a 5 años;
blanco = 2 años para estudio bianual). Retorna diccionario de
agregados puros, sin PII:

- `beneficiarios_por_cohorte_anio`: conteo por año de cohorte
  (desde `convocatoria.ano`) y estado académico (`AcademicRecord.status`).
- `tasa_graduacion`: graduados / total expedientes en rango de años.
- `tasa_retorno`: con `retorno_archipelago=True` / total annotable
  en rango (excluye `null`).
- `montos_por_ies`: suma de `DisbursementAuthorization.amount`
  agrupada por `ies_nombre` normalizado; k=3: celdas con <3
  beneficiarios se reclasifican a `"Otros (suprimido)"`.
- `beneficiarios_por_municipio`: conteo agrupado por `municipio_origen`;
  k=3 igual supresión.
- `desglose_por_nivel_formacion`: desde `Solicitud.datos_academicos.nivel_formacion`.
- `desglose_por_convocatoria`: resumen de beneficiarios y montos
  por convocatoria en el rango.

Regla monetaria verificada (AGENTS.md §6 Regla 5): los montos girados
provienen de `DisbursementAuthorization.amount` (PKgsql Decimal(12,2));
el test fixture calcula la suma a mano para verificar la agregación.

### 5. Endpoint de estudio de impacto

**`apps/reporting/urls.py`** + **`apps/reporting/views.py`**:

```
GET /api/reporting/estudio-impacto/
    ?anio_inicio=<int>
    &anio_fin=<int>
```

- Permiso: `HasAnyRole(REPORT_ROLES + ["R-CT"])` donde
  `REPORT_ROLES = ["R-COORD", "R-JUNTA", "R-SECEDU", "R-ADMIN"]`
  (`apps/reporting/views.py:14`). Se añade `R-CT` porque el CT es
  el actor responsable del estudio (`project.md §6.1.2`).
- Retorna `400` si: `anio_inicio` falta o no es numérico,
  `anio_fin` falta o no es numérico, `anio_fin < anio_inicio`,
  rango > 4 años (`anio_fin - anio_inicio > 4`).
- Respuesta: JSON con la estructura del servicio, sin PII.

### 6. Anotación de retorno al Archipiélago

**`apps/academic_tracking/views.py`** — nuevo `action` en
`AcademicRecordViewSet` (ruta `/api/academic-tracking/records/{id}/`):

```
PATCH /api/academic-tracking/records/{id}/anotar_retorno/
    Body: {"retorno_archipelago": true|false}
```

- Permiso: `_AcademicManagementPermission` (R-COORD, R-ADMIN;
  R-CT no tiene acceso de escritura a academic_tracking en `project.md §7.2`).
- Valida que el campo acepte el valor booleano.
- Genera evento de auditoría CAP-022 via `log_audit_event` con
  fail-closed: si la escritura de auditoría falla, se revierte la
  anotación con `transaction.atomic` (rollback).
- Audit action: `academic_retorno_annotate`.

## Criterios de aceptación

- [ ] El comando `backfill_impact_fields --dry-run` emite contadores sin escribir en BD.
- [ ] `ies_nombre` queda poblado para todas las solicitudes que tengan `datos_academicos.institucion`.
- [ ] `municipio_origen` se asigna solo si `datos_personales.municipio` coincide exactamente (casefold) con un código del catálogo `MunicipioIsla`; sin match → `null`.
- [ ] El estudio de impacto agrupa por `ies_nombre` normalizado (no variantes crudas del texto libre).
- [ ] Las celdas con <3 beneficiarios se suprimen en los desgloses por IES y por municipio; el total de "Otros (suprimido)" se reporta separadamente.
- [ ] El endpoint `/api/reporting/estudio-impacto/` requiere uno de los roles `REPORT_ROLES` o `R-CT`; retorna `403` para usuarios autenticados sin rol y `401` para anónimos.
- [ ] La respuesta del endpoint no contiene nombres, documentos, correos ni datos que identifiquen individualmente a un beneficiario.
- [ ] La anotación de `retorno_archipelago` genera un evento de auditoría y falla closed si la auditoría no se persiste.
- [ ] La suite de tests completa corre verde en SQLite (CI corre en PostgreSQL).
- [ ] `manage.py check` y `makemigrations --check` no reportan errores tras aplicar las migraciones.

## Pruebas

### Unitarias del backfill

- `test_match_institucion`: parsea `"Universidad Nacional  de Colombia"` → `"Universidad Nacional de Colombia"` (espacios colapsados).
- `test_no_match_municipio`: `datos_personales.municipio = "bogota"` → `municipio_origen` queda `null`.
- `test_match_municipio`: `datos_personales.municipio = "san_andres"` → FK resuelta.
- `test_idempotencia`: comando ejecutado dos veces → sin duplicados; contadores de actualización idem.
- `test_dry_run_no_write`: `--dry-run` → ninguna fila modificada en BD.

### Unitarias del servicio

- `test_montos_suman_contra_fixture`: dados 3 desembolsos conocidos (50, 100, 150), la suma por IES reporta 300.
- `test_k_suppression_ies`: 2 beneficiarios en IES "X", 5 en IES "Y" → "X" aparece en "Otros (suprimido)"; "Y" con su nombre.
- `test_k_suppression_municipio`: análogo para municipios.
- `test_rango_invalido`: `anio_inicio=2024, anio_fin=2023` → `ValueError`.
- `test_rango_excede_5`: `anio_inicio=2020, anio_fin=2026` → `ValueError`.
- `test_tasa_retorno`: mix de `retorno_archipelago=True/False/null` → tasa calcula correctamente (null excluido del denominador).

### Integración de endpoints

- `test_r_ct_200`: usuario con `R-CT` → `200`.
- `test_anonimo_401`: sin autenticación → `401`.
- `test_sin_rol_403`: usuario autenticado sin rol → `403`.
- `test_params_invalidos_400`: anio_inicio faltante, rango inválido → `400` con mensaje descriptivo.

### Anotación de retorno

- `test_anotacion_retorno_genera_audit`: PATCH exitoso → evento en tabla `audit_AuditEvent` con `action=academic_retorno_annotate`.
- `test_anotacion_audit_fail_rollback`: falla simulada de auditoría → `AcademicRecord.retorno_archipelago` sin cambios.
- `test_permiso_escritura_sin_rol`: usuario sin `R-COORD` ni `R-ADMIN` → `403`.

### Migraciones

- `makemigrations --check` en `apps/applications` y `apps/academic_tracking` tras aplicar migraciones del change.

## Riesgos y Fuera del alcance

### Riesgos

| Riesgo | Mitigación |
|---|---|
| Variantes de nombre de IES sin sinónimos normalizados ("UNAL", "Universidad Nacional de Colombia", "Univ. Nacional") | Agrupación por casefold + documentación de limitación; normalización de sinónimos queda como mejora futura (CHG-5xx). |
| Clave `municipio` diferente si cambia el template del wizard | Backfill lee la clave `municipio` (verificada en `wizard_step_1.html:84`); si cambia, el backfill reporta "sin-match". |
| Catálogo `MunicipioIsla` sembrado manualmente puede estar incompleto | `SET_NULL` tolera registros faltantes; el backfill reporta contadores de sin-match. |
| Re-identificación en celdas pequeñas (k=3) | k=3 aplicado en desgloses; celdas suprimidas van a "Otros (suprimido)"; umbral alineado con Ley 1581/2012. |
| Rendimiento del backfill con miles de solicitudes | `iterator()` + `batch_size=500`; indexar `convocatoria__ano` y `estado` si aún no existe. |

### Fuera del alcance

- Normalización de sinónimos de IES (ej. UNAL = Universidad Nacional de Colombia).
- Publicación pública del estudio (capa de CHG-504, con su propio umbral k si aplica).
- Generación de PDF del estudio de impacto.
- Seed del catálogo `TipoIes` (solo se siembran los tres `MunicipioIsla`).
- Integraciones con sistemas externos (SNIES, SISBÉN, OCCRE, bancos) — vedadas por `project.md §8.1`.
