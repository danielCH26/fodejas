# CHG-505 Export Auditoría Externa

## Contexto

CAP-028 (Auditoría Externa — exportación a entes de control, P1) se
cataloga en `project.md` §8:611 como capacidad de prioridad alta cuyo
primer entregable definido en `project.md` §14.3 (línea 1113) requiere:

> Formato CSV y JSONL. Conjuntos de datos alineados con los reportes de
> la Gobernación. Sellado de tiempo + firma.

El groundwork ya existe: la bitácora inmutable con hash chain (CAP-022,
P0) fue implementada en `apps/audit/services.py` con
`calculate_hash()` (SHA-256 sobre
`timestamp|actor_id|action|entity|entity_id|changes_str|previous_hash`),
`log_audit_event()` con `pg_advisory_xact_lock(253977205)` (CHG-801 /
AUD-003), y `verify_chain()` que valida la cadena completa. La función
`get_audit_events()` en `apps/audit/selectors.py` ofrece filtros por
actor, acción, entidad, módulo y rango de timestamps. El rol R-AUDITOR
(tipo externo, "Acceso de solo lectura a bitácora, reportes y datos
para fines de fiscalización") está sembrado en
`apps/accounts/management/commands/seed_roles.py` línea 69.

La brecha es que no existe ningún endpoint de exportación y que el
serializer interno (`AuditEventSerializer`, `apps/audit/serializers.py`)
expone `actor_email` (PII), campo que no puede viajar al export porque:
(a) no está cubierto por el hash del chain y (b) la Ley 1581/2012
(`project.md` §13.2, línea 1051) exige minimización de PII en reportes.

El roadmap (`roadmap.md` línea 435) señala `apps/audit/` y
`apps/reporting/` como apps afectadas; el entregable verificable
(`roadmap.md` línea 449) es: *"Un ente de control puede descargar un
paquete de datos sellado y firmado."*

## Capacidades afectadas

- **CAP-028** (primaria) — Auditoría Externa (exportación a entes de
  control). `apps/audit/`, `apps/reporting/`.
- **CAP-022** — Bitácora de Auditoría (inmutable). La capacidad de
  exportar lee eventos existentes sin modificar la escritura ni el
  mecanismo de encadenamiento existente.

## Reglas de negocio afectadas

- `project.md` §14.3 (línea 1113) — Exportación para Entes de Control
  (R-AUDITOR): CSV y JSONL, conjuntos alineados con reportes de la
  Gobernación, sellado de tiempo + firma.
- `project.md` §13.3 (línea 1060) — Bitácora de Auditoría: append-only
  con hash chain, timestamp UTC, actor, acción, entidad, id,
  before/after, IP, user-agent, módulo; retención 20 años; exportación a
  entes de control.
- `project.md` §13.2 (línea 1049) — Protección de Datos Personales:
  cumplimiento Ley 1581/2012, enmascaramiento de PII en reportes.
- `AGENTS.md` §7 — Insertar eventos de auditoría desde servicio o
  contexto, nunca desde la vista. La exportación lee del servicio
  existente sin cambiar esta regla.

## Cambios propuestos

### 1. Permisos (`apps/accounts/permissions.py`)

Nueva clase `IsAuditExporter` basada en el patrón `HasAnyRole`
(`permissions.py` líneas 73-84):

```python
class IsAuditExporter(permissions.BasePermission):
    AUDIT_EXPORT_ROLES = ["R-ADMIN", "R-CONTROL", "R-AUDITOR"]
```

No modifica `IsAuditViewer` (interno UI mantiene `["R-ADMIN", "R-CONTROL"]`).

### 2. Servicio de exportación (`apps/audit/export.py`)

Columnas permitidas (whitelist, `AUDIT_EXPORT_COLUMNS`) — campos cubiertos por el
hash chain o metadata pública, **sin PII derivada no cubierta por el
hash**:

```
id, timestamp, actor_id, actor_is_system, action, entity,
entity_id, changes (JSON verbatim), ip_address, user_agent,
module, previous_hash, current_hash
```

`build_export_row(event)` serializa `changes` con
`json.dumps(changes, sort_keys=True, default=str)` — idéntico al
algoritmo de `services.calculate_hash()` para garantizar round-trip
verbatim. `actor_email` y `actor.username` se excluyen deliberadamente.

Generación CSV (`csv.DictWriter`) y JSONL (`json.dumps` por línea)
sobre `.iterator()` de Django para streaming.

SHA-256 del payload completo se computa en pasada previa sobre el
mismo iterator (se materializa a `BytesIO` antes de retornar la
respuesta streaming).

### 3. Endpoint API (`apps/audit/views.py` + `urls.py`)

```
GET /api/audit/export/
    ?from=<ISO datetime>       # opcional, timestamp__gte
    &to=<ISO datetime>         # opcional, timestamp__lte
    &entity=<string>           # opcional, entity__iexact
    &action=<string>           # opcional, action__iexact
    &format=csv | jsonl        # requerido

Permisos: IsAuditExporter
```

Validación de parámetros:

- `format` omitido o valor desconocido → HTTP 400 + detalle.
- `from` > `to` → HTTP 400.
- Los demás parámetros opcionales; queryset vacío → respuesta vacía (200).

Encabezados de manifiesto de verificación en cada respuesta:

| Header | Valor |
|---|---|
| `X-Audit-Event-Count` | Número de eventos en el export |
| `X-Audit-Chain-Valid` | `true` / `false` (resultado de `verify_chain()`) |
| `X-Audit-Chain-Head` | Hash del último evento de la cadena |
| `X-Audit-Chain-Break` | UUID del evento donde se rompió la cadena, o `null` |
| `X-Audit-Export-SHA256` | SHA-256 del payload exportado |
| `X-Audit-Generated-At` | Timestamp UTC ISO del momento de generación |
| `Content-Disposition` | `attachment; filename="fodejas-audit-YYYY-MM-DD.ext"` |

### 4. Sellado de tiempo lite (primera iteración)

El sellado real con firma digital se difiere a CAP-029
(`AGENTS.md` §7: servicio abstracto `signer.py`). Esta primera
iteración implementa el "sello lite": `X-Audit-Generated-At` + resultado
de `verify_chain()` + SHA-256 del payload en header. No se integra TSA
externo (`AGENTS.md` §6 Regla 2: ninguna integración externa).

## Criterios de aceptación

- [ ] Usuario con rol R-AUDITOR (sin R-ADMIN ni R-CONTROL) obtiene HTTP
      200 al hacer GET `/api/audit/export/?format=csv`.
- [ ] Usuario autenticado sin ninguno de los tres roles → HTTP 403.
- [ ] Solicitud anónima (no autenticada) → HTTP 401.
- [ ] `format=csv` devuelve contenido CSV parseable con
      `csv.DictReader`; cada fila tiene las 13 columnas permitidas.
- [ ] `format=jsonl` devuelve una línea JSON por evento, parseable
      individualmente con `json.loads()`.
- [ ] El SHA-256 calculado sobre el body descargado es idéntico al
      valor del header `X-Audit-Export-SHA256`.
- [ ] Para un evento con `changes = {"before": {"foo": 1}, "after":
      {"foo": 2}}`, el campo `changes` en la descarga es la cadena JSON
      exacta almacenada (round-trip `json.loads` → `json.dumps` idéntico).
- [ ] Ninguna fila del export contiene `actor_email` ni nombre del actor.
- [ ] Los headers de manifiesto (`X-Audit-*`) están presentes en toda
      respuesta 200.
- [ ] El filtro `from=2025-01-01T00:00:00Z&to=2025-06-30T23:59:59Z`
      retorna únicamente eventos dentro del rango.
- [ ] El filtro `entity=Convocatory` retorna solo eventos de esa
      entidad.
- [ ] El filtro `action=CREATE` retorna solo eventos de esa acción.
- [ ] `format=xml` (formato inválido) retorna HTTP 400.

## Pruebas

- **Permisos**: `test_audit_export_as_auditor_returns_200`,
  `test_audit_export_without_role_returns_403`,
  `test_audit_export_anonymous_returns_401`.
- **Formatos**: `test_audit_export_csv_parseable`,
  `test_audit_export_jsonl_parseable_line_by_line`,
  `test_audit_export_columns_match_whitelist_no_pii`.
- **Veracidad**: `test_audit_export_changes_round_trip_identical`,
  `test_audit_export_body_sha256_matches_header`.
- **Filtros**: `test_audit_export_filter_by_from_to`,
  `test_audit_export_filter_by_entity`, `test_audit_export_filter_by_action`.
- **Validación**: `test_audit_export_invalid_format_returns_400`,
  `test_audit_export_invalid_date_range_returns_400`.
- **Streaming**: `test_audit_export_streaming_returns_iterator_not_list`.

## Riesgos y Fuera del alcance

### Riesgos

1. **PII en `changes` verbatim**: el Verbatim Export Principle exige que
   `changes` se exporte sin alteración para mantener la verificabilidad
   del hash chain (cambios parciales romperían `current_hash` de todos
   los eventos posteriores). Mitigación: `actor_email` se excluye de
   las columnas permitidas; el documento de decisión (este proposal)
   registra la justificación. Los entes de control tienen cobertura
   legal bajo Ley 1581/2012 Art. 6h para tratamiento en interés del
   titular.

2. **Costo de `verify_chain()` en volumen grande**: la función escanea
   la cadena completa (20 años de eventos) en cada petición. Mitigación:
   primera iteración acepta el costo; windowing deferido a iteración
   posterior.

3. **Sellado de tiempo y firma reales diferidos**: la firma digital se
   implementa en CAP-029 (servicio abstracto `signer.py` en
   `apps/legalization/`). Sin firma, el "sello" de esta iteración es
   lite (timestamp + hash del payload). No se propone integración con
   TSA externo (`AGENTS.md` §6 Regla 2).

4. **Volumen de datos para 20 años de eventos**: streaming con
   `.iterator()` mitiga memoria; filtros por rango son recomendados
   en la documentación del endpoint.

### Fuera del alcance

- Firma digital real (CAP-029).
- Integración con TSA externo (Regla 2 de `AGENTS.md` §6).
- Interfaz HTML de exportación.
- Exportación de entidades no-audit (actos administrativos,
  desembolsos, convocatorias).
- Scrubbing o reencoding de `changes` (rompería la verificabilidad del
  hash chain).
- API de verificación incremental del chain.
