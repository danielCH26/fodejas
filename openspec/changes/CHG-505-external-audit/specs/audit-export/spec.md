# audit-export/spec.md — CHG-505 Export Auditoría Externa

## ADDED

### A. Permisos de exportación

**SHALL** restringir el acceso al endpoint de exportación exclusivamente a
usuarios autenticados que posean al menos uno de los roles
`R-ADMIN`, `R-CONTROL` o `R-AUDITOR`.

**SHALL** retornar código HTTP 401 (Unauthorized) cuando la solicitud
proviene de un usuario no autenticado.

**SHALL** retornar código HTTP 403 (Forbidden) cuando el usuario
autenticado no posee ninguno de los roles autorizados.

**SHALL** permitir acceso a usuarios con `is_superuser=True` o
`is_staff=True` independientemente de la asignación explícita de roles.

**SHALL** no modificar la clase de permisos `IsAuditViewer` existente;
dicha clase seguirá permitiendo únicamente `R-ADMIN` y `R-CONTROL` para
accesos internos de la plataforma.

---

### B. Formatos de exportación

**SHALL** soportar el formato CSV conforme a lo definido en
`project.md` §14.3 (línea 1113), generando un archivo delimitado por
comas con encabezados en la primera fila.

**SHALL** soportar el formato JSONL (JSON Lines) conforme a lo definido
en `project.md` §14.3 (línea 1113), generando una línea JSON por cada
evento de auditoría exportado.

**SHALL** incluir exclusivamente las siguientes columnas en el export
(orden no estricto):

```
id, timestamp, actor_id, actor_is_system, action, entity,
entity_id, changes, ip_address, user_agent, module,
previous_hash, current_hash
```

**SHALL** excluir deliberadamente de toda fila del export los campos
`actor.email`, `actor.username` y cualquier otro identificador de PII
del actor no cubierto por el hash del chain. Esta exclusión se fundamenta
en la obligación de minimización de PII establecida en
`project.md` §13.2 (línea 1049) y la Ley 1581/2012.

**SHALL** exportar el campo `changes` como la cadena JSON exacta
almacenada en la base de datos (sin prettify ni reordenamiento), de
modo que la verificación del hash SHA-256 del payload sea posible y la
cadena de hash de la bitácora (`project.md` §13.3, línea 1060) no se
invalide.

---

### C. Endpoint de exportación

**SHALL** exponer el endpoint `GET /api/audit/export/` en la API REST.

**SHALL** aceptar el parámetro de query `format` con valores
`csv` o `jsonl`; ante un valor no reconocido, **SHALL** retornar
HTTP 400 con mensaje de error.

**SHALL** aceptar los parámetros opcionales de filtro: `from`
(timestamp mínimo, inclusivo), `to` (timestamp máximo, inclusivo),
`entity` (nombre de entidad, comparación case-insensitive),
`action` (tipo de acción).

**SHALL** retornar HTTP 400 cuando el valor de `from` sea posterior al
valor de `to`.

**SHALL** retornar una respuesta vacía con código HTTP 200 (y headers
de manifiesto) cuando el queryset filtrado no contiene eventos.

---

### D. Encabezados de manifiesto de verificación

**SHALL** incluir en toda respuesta HTTP 200 los siguientes encabezados:

| Encabezado | Descripción |
|---|---|
| `X-Audit-Event-Count` | Cantidad total de eventos incluidos en el export |
| `X-Audit-Chain-Valid` | `true` si `verify_chain()` retorna `is_valid=True`; `false` en caso contrario |
| `X-Audit-Chain-Head` | Hash SHA-256 del último evento en la cadena al momento de la generación |
| `X-Audit-Chain-Break` | UUID del evento donde se detectó ruptura de cadena, o `null` |
| `X-Audit-Export-SHA256` | Hash SHA-256 calculado sobre el payload completo del archivo exportado |
| `X-Audit-Generated-At` | Timestamp UTC en formato ISO 8601 del momento de generación del export |

**SHALL** incluir el encabezado `Content-Disposition` con valor
`attachment; filename="fodejas-audit-YYYY-MM-DD.<ext>"`, donde
`<ext>` es `csv` o `jsonl` según el formato solicitado.

---

### E. Integridad y verificabilidad

**SHALL** garantizar que el SHA-256 del cuerpo (body) del archivo
descargado sea bit-a-bit idéntico al valor del encabezado
`X-Audit-Export-SHA256`.

**SHALL** computar el hash de verificación del payload en una pasada
previa sobre la totalidad de los eventos antes de iniciar el streaming
de la respuesta HTTP.

**SHALL** consumir los eventos de auditoría mediante iteración perezosa
(`.iterator()` de Django QuerySet) para evitar cargar el conjunto
completo en memoria.

**SHALL** invocar `verify_audit_chain()` de `apps/audit/services.py`
para determinar el estado de integridad de la cadena al momento de la
generación del export.

---

### F. Sellado de tiempo (primera iteración)

**SHALL** registrar el timestamp de generación del export en el
encabezado `X-Audit-Generated-At` como evidencia de instante de
emisión.

**SHALL** registrar el resultado de integridad de cadena en
`X-Audit-Chain-Valid`, `X-Audit-Chain-Head` y `X-Audit-Chain-Break`
como evidencia de estado del ledger al momento de la emisión.

**SHALL** registrar el hash SHA-256 del payload en
`X-Audit-Export-SHA256` como evidencia de contenido exacto.

La firma digital sobre el paquete de export **SHALL** ser diferida a la
implementación de CAP-029 (servicio abstracto `signer.py` en
`apps/legalization/`, referenced in `AGENTS.md` §7).

---

### G. Escenarios

#### G-1: Auditor externo descarga JSONL y verifica SHA-256

**GIVEN** un usuario autenticado con rol `R-AUDITOR`
**WHEN** solicita `GET /api/audit/export/?format=jsonl`
**THEN** el servidor retorna HTTP 200 con Content-Type `application/x-ndjson`
         y `Content-Disposition: attachment; filename="fodejas-audit-<date>.jsonl"`
         y cuerpo consistente en líneas JSON, una por evento,
         sin campos `actor.email` ni `actor.username`,
         y SHA-256 del cuerpo coincide con `X-Audit-Export-SHA256`.

#### G-2: Usuario sin rol recibe 403

**GIVEN** un usuario autenticado sin los roles `R-ADMIN`, `R-CONTROL` ni `R-AUDITOR`
**WHEN** solicita `GET /api/audit/export/?format=csv`
**THEN** el servidor retorna HTTP 403.

#### G-3: changes verbatim round-trip

**GIVEN** un evento de auditoría con
         `changes = {"before": {"foo": 1}, "after": {"foo": 2}}`
**WHEN** se exporta ese evento en cualquier formato soportado
**THEN** el campo `changes` en el archivo exportado es la cadena JSON
         `{"after": {"foo": 2}, "before": {"foo": 1}}` (claves ordenadas
         igual que en `services.calculate_hash()`), y dicha cadena es
         parte del payload sobre el cual se computó `X-Audit-Export-SHA256`.

#### G-4: Formato inválido retorna 400

**GIVEN** un usuario autenticado con rol `R-AUDITOR`
**WHEN** solicita `GET /api/audit/export/?format=xml`
**THEN** el servidor retorna HTTP 400 con `{"detail": "..."}`.

---

### H. Referencias

- CAP-028 — Auditoría Externa (exportación a entes de control),
  `project.md` §8:611
- `project.md` §14.3 (línea 1113) — Exportación para Entes de Control
  (R-AUDITOR): CSV, JSONL, sellado de tiempo + firma
- `project.md` §13.3 (línea 1060) — Bitácora de Auditoría:
  append-only hash chain, timestamp UTC, actor, acción, entidad, id,
  before/after, IP, user-agent, módulo; retención 20 años; exportación
  a entes de control
- `project.md` §13.2 (línea 1049) — Protección de Datos Personales:
  Ley 1581/2012, minimización de PII
- `AGENTS.md` §7 — Insertar eventos de auditoría desde servicio o
  contexto, nunca desde la vista; hash chain; firma electrónica
  abstracta via CAP-029
- `AGENTS.md` §6 Regla 2 — Prohibición de integraciones externas
  (SNIES, SISBÉN, OCCRE, bancos, TSA)
