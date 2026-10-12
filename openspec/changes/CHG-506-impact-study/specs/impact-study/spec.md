# spec.md — CHG-506 Estudio de Impacto (CAP-027)

## ADDED

### Solicitud — nuevo campo `ies_nombre`

```python
ies_nombre = models.CharField(max_length=255, blank=True, null=True)
```

- SHALL almacenar el nombre normalizado de la IES donde estudia el
  beneficiario, derivado de `datos_academicos.institucion` del FUI.
- SHALL normalizar el valor con `strip()` y colapso de espacios
  múltiples (`re.sub(r' {2,}', ' ', ...)`) en el método `save()`
  del modelo.
- SHALL permitir `null` cuando `datos_academicos.institucion` esté
  ausente o el backfill no haya sido ejecutado.

### Solicitud — nuevo campo `municipio_origen`

```python
municipio_origen = models.ForeignKey(
    "core.MunicipioIsla",
    on_delete=models.SET_NULL,
    null=True,
    blank=True,
)
```

- SHALL referenciar el municipio/isla de residencia del aspirante,
  derivado de `datos_personales.municipio` en el FUI.
- SHALL usar `on_delete=SET_NULL` para tolerar la ausencia de filas
  en el catálogo `MunicipioIsla` y no bloquear el borrado del
  catálogo.
- SHALL permitir `null` cuando no haya match entre el código del
  formulario y los códigos del catálogo.

### AcademicRecord — nuevo campo `retorno_archipelago`

```python
retorno_archipelago = models.BooleanField(null=True, blank=True)
```

- SHALL registrar si el beneficiario retornó al Archipiélago
  después de sus estudios.
- SHALL ser `null` cuando no se ha realizado la anotación.
- SHALL ser modificable solo mediante endpoint de anotación
  con permisos de escritura y auditoría CAP-022.

### ReportingService — método `estudio_impacto`

```python
@staticmethod
def estudio_impacto(anio_inicio: int, anio_fin: int) -> dict:
    ...
```

- SHALL retornar un diccionario con los siguientes claves:
  `beneficiarios_por_cohorte_anio`, `tasa_graduacion`,
  `tasa_retorno`, `montos_por_ies`, `beneficiarios_por_municipio`,
  `desglose_por_nivel_formacion`, `desglose_por_convocatoria`.
- SHALL calcular `tasa_retorno` como
  `count(retorno_archipelago=True) /
   count(retorno_archipelago__isnull=False)`;
  SHALL excluir filas con `null` del denominador.
- SHALL agrupar montos por `ies_nombre` (campo normalizado del
  modelo `Solicitud`, no el JSON blob).
- SHALL aplicar supresión k=3 en `montos_por_ies` y
  `beneficiarios_por_municipio`: cualquier celda con menos de
  3 beneficiarios individuales SHALL ser reclasificada a la
  categoría `"Otros (suprimido)"`; los montos correspondientes
  SHALL agregarse a esa categoría.
- SHALL validar que `1 <= anio_fin - anio_inicio <= 4`; de lo
  contrario SHALL elevar `ValueError`.
- SHALL retornar únicamente agregados; SHALL NO incluir nombres,
  documentos, correos ni datos que permitan identificar a un
  beneficiario individual.

### Endpoint — GET `/api/reporting/estudio-impacto/`

| Atributo | Valor |
|---|---|
| Método | GET |
| Path | `/api/reporting/estudio-impacto/` |
| Query params | `anio_inicio` (int, requerido), `anio_fin` (int, requerido) |
| Permiso | `HasAnyRole(["R-COORD", "R-JUNTA", "R-SECEDU", "R-ADMIN", "R-CT"])` |
| 200 | Diccionario de agregados del servicio |
| 400 | Params inválidos (`anio_inicio`/`anio_fin` faltantes, `anio_fin < anio_inicio`, rango > 4 años) |
| 401 | Anónimo |
| 403 | Usuario autenticado sin rol |

- SHALL invocar `ReportingService.estudio_impacto(anio_inicio, anio_fin)`.
- SHALL delegar la validación del rango de años al servicio.

### Endpoint — PATCH `/api/academic-tracking/records/{id}/anotar_retorno/`

| Atributo | Valor |
|---|---|
| Método | PATCH |
| Path | `/api/academic-tracking/records/{id}/anotar_retorno/` |
| Body | `{"retorno_archipelago": true\|false}` |
| Permiso | `_AcademicManagementPermission` (R-COORD, R-ADMIN) |
| 200 | `{"retorno_archipelago": <valor>}` |
| 400 | Body inválido o ID no existe |
| 403 | Usuario sin permiso de escritura en academic_tracking |

- SHALL persistir `AcademicRecord.retorno_archipelago` con el valor
  del body.
- SHALL invocar `log_audit_event(action="academic_retorno_annotate", ...)`
  dentro de la misma transacción.
- SHALL hacer rollback de la anotación si la escritura del evento
  de auditoría falla (fail-closed).

### Comando — `backfill_impact_fields`

- SHALL parsear `datos_academicos.institucion` → `ies_nombre`
  normalizado (strip + colapso de espacios) para cada `Solicitud`.
- SHALL resolver `datos_personales.municipio` contra
  `MunicipioIsla.codigo` (casefold) → `municipio_origen` FK.
- SHALL asignar `null` cuando no haya match y registrar el
  conteo de sin-match.
- SHALL ser idempotente: SHALL escribir solo si el valor destino
  difiere del valor actual.
- SHALL con `--dry-run` emitir el reporte de contadores sin abrir
  transacción de escritura.
- SHALL usar `iterator(chunk_size=500)` para limitar uso de memoria.

### Seed — MunicipioIsla

- SHALL sembrar las siguientes filas en `core.MunicipioIsla`
  (1:1 con los tres valores del select `municipio` del FUI,
  `wizard_step_1.html:86-88`):
  (`san_andres`, "San Andrés", orden=1),
  (`providencia`, "Providencia", orden=2),
  (`santa_catalina`, "Santa Catalina", orden=3).
  Nota: administrativamente Santa Catalina pertenece al municipio de
  Providencia (DANE), pero el catálogo modela islas y el FUI ofrece
  tres opciones; sembrar las tres maximiza la resolución del backfill.
- SHALL ser idempotente (`get_or_create`).
- SHALL ser ejecutable múltiples veces sin duplicados.

## Scenarios

### Scenario: k-supresión en desglose por municipio

```
GIVEN 3 beneficiarios con municipio_origen=San Andrés,
      2 beneficiarios con municipio_origen=Providencia,
      1 beneficiario con municipio_origen=Santa Catalina
WHEN  ReportingService.estudio_impacto(anio_inicio, anio_fin)
THEN  la respuesta contiene:
      {"municipio": "San Andrés", "beneficiarios": 3}
      {"municipio": "Otros (suprimido)", "beneficiarios": 3}
      // Providencia (2) y Santa Catalina (1) < 3 → suprimidas y
      // sumadas (2+1=3); San Andrés (3) >= 3 se mantiene
```

### Scenario: backfill idempotente

```
GIVEN Solicitud con datos_academicos.institucion="Universidad  Nacional"
WHEN  se ejecuta backfill_impact_fields dos veces
THEN  ies_nombre = "Universidad Nacional" tras la primera ejecución
      ies_nombre = "Universidad Nacional" sin cambios tras la segunda
      // no se duplican actualizaciones
```

### Scenario: R-CT accede al estudio de impacto

```
GIVEN un usuario autenticado con rol R-CT
WHEN  GET /api/reporting/estudio-impacto/?anio_inicio=2023&anio_fin=2024
THEN  respuesta 200 con agregados
```

### Scenario: usuario sin rol recibe 403 en estudio de impacto

```
GIVEN un usuario autenticado sin roles REPORT_ROLES ni R-CT
WHEN  GET /api/reporting/estudio-impacto/?anio_inicio=2023&anio_fin=2024
THEN  respuesta 403
```

### Scenario: anotación retorno genera evento de auditoría

```
GIVEN AcademicRecord con retorno_archipelago=null
WHEN  PATCH /api/academic-tracking/records/{id}/anotar_retorno/
      con {"retorno_archipelago": true}
THEN  AcademicRecord.retorno_archipelago = True
      existe registro en audit_AuditEvent
      con action="academic_retorno_annotate"
```

### Scenario: fallo de auditoría revierte anotación

```
GIVEN AcademicRecord con retorno_archipelago=null
WHEN  log_audit_event falla (simulada en test)
      y se invoca la anotación
THEN  AcademicRecord.retorno_archipelago permanece null
      // rollback de la transacción
```

## Referencias

- CAP-027 — Estudio de Impacto (`project.md §8`, línea 610)
- `project.md §14.2` — Estadísticas de impacto bianuales
  (Art. 20.f Manual Operativo como referencia normativa)
- `project.md §6.1.2` — CT responsable del estudio de impacto
  (línea 456)
- `project.md §13.2` — Protección de datos personales, Ley 1581/2012
  (línea 1049-1059)
- `project.md §7` — Roles (R-CT en línea 542)
- `apps/reporting/views.py:14` — `REPORT_ROLES`
- `apps/core/models.py:63` — `MunicipioIsla`
- `apps/applications/models.py` — `Solicitud`
- `apps/academic_tracking/models.py` — `AcademicRecord`
- `apps/audit/` — CAP-022 Bitácora de Auditoría
