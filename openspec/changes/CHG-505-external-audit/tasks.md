# Tasks — CHG-505 Export Auditoría Externa

## 1. Permisos

- [ ] 1.1 Definir `AUDIT_EXPORT_ROLES = ["R-ADMIN", "R-CONTROL",
      "R-AUDITOR"]` y crear clase `IsAuditExporter` en
      `apps/accounts/permissions.py`, siguiendo el patrón
      `HasAnyRole`. Superusers y staff deben ser permitidos
      (`is_superuser or is_staff → True`).
- [ ] 1.2 No modificar `IsAuditViewer` existente (interno UI se
      mantiene con `["R-ADMIN", "R-CONTROL"]`).

## 2. Servicio de exportación (`apps/audit/`)

- [ ] 2.1 Crear `apps/audit/export.py`:
  - Definir `AUDIT_EXPORT_COLUMNS` como tupla de 14 nombres de campo
    (`id`, `timestamp`, `actor_id`, `actor_is_system`, `action`,
    `entity`, `entity_id`, `changes`, `ip_address`, `user_agent`,
    `module`, `previous_hash`, `current_hash`).
  - Implementar `build_export_row(event)` que retorne un dict con las
    columnas blancas; `changes` se serializa con
    `json.dumps(changes, sort_keys=True, default=str)` — idéntico
    al algoritmo de `services.calculate_hash()` para garantizar
    round-trip verbatim. Se excluye deliberadamente `actor_email` y
    nombre del actor.
- [ ] 2.2 Implementar generadores `iter_csv(events)` y
      `iter_jsonl(events)` sobre iteradores de QuerySet Django:
  - CSV: `csv.DictWriter(sys.stdout, fieldnames=AUDIT_EXPORT_COLUMNS,
    extrasaction="ignore")`.
  - JSONL: `json.dumps(row, sort_keys=True, default=str)` por línea.
  - Ambos deben usar `.iterator()` del QuerySet para streaming real.
- [ ] 2.3 Implementar función `compute_payload_sha256(events_iter)` que
      materialice el payload completo a `BytesIO`, compute SHA-256, y
      retorne `(payload_bytes, hex_digest)`. Se llama en pasada previa
      antes de servir la respuesta streaming.

## 3. Endpoint API

- [ ] 3.1 Crear vista `AuditExportView` en `apps/audit/views.py`:
  - Decorador `@permission_classes([IsAuditExporter])`.
  - Leer query params: `from`, `to` (datetime), `entity` (string),
    `action` (string), `format` (csv | jsonl).
  - Validar: `format` no csv/jsonl → `Response({"detail": ...},
    status=400)`; `from > to` → 400.
  - Construir queryset filtrado con `get_audit_events()` de
    `selectors.py`.
  - En pasada previa: invocar `compute_payload_sha256(events_iter)` para
    obtener payload y digest.
  - Invocar `verify_audit_chain()` para obtener estado de cadena.
  - Retornar `StreamingHttpResponse` con generador CSV o JSONL.
  - Adjuntar headers de manifiesto: `X-Audit-Event-Count`,
    `X-Audit-Chain-Valid`, `X-Audit-Chain-Head`,
    `X-Audit-Chain-Break`, `X-Audit-Export-SHA256`,
    `X-Audit-Generated-At` (UTC ISO), `Content-Disposition`.
- [ ] 3.2 Registrar ruta en `apps/audit/urls.py`:
    `path("export/", AuditExportView.as_view(), name="audit-export")`.

## 4. Pruebas (`apps/audit/tests/test_export.py`)

- [ ] 4.1 **Permisos**: fixture con `User + R-AUDITOR` → 200; fixture
      sin rol → 403; cliente anónimo → 401.
- [ ] 4.2 **Formatos**: CSV — `csv.DictReader` sobre response.content
      genera filas con las 14 columnas exactas, sin `actor_email`.
      JSONL — cada línea es `json.loads`-eable; cada objeto tiene las
      14 claves.
- [ ] 4.3 **Veracidad**: `changes` de un evento UPDATE se exporta;
      `json.loads(exported_changes)` ==
      `json.loads(stored_changes)`. SHA-256 del body (httpx o
      `hashlib.sha256(response.content)`) == header
      `X-Audit-Export-SHA256`.
- [ ] 4.4 **Filtros**: `from/to` acota el rango de timestamps visible;
      `entity` filtra por nombre exacto; `action` filtra por tipo.
- [ ] 4.5 **Validación**: `format=xml` → 400; `from` posterior a `to`
      → 400.

## 5. Verificación final

- [ ] 5.1 `pytest apps/audit/` — todas las pruebas verdes en SQLite
      (suite local); PostgreSQL se valida en CI.
- [ ] 5.2 `python manage.py check` — sin warnings ni errores.
- [ ] 5.3 `python manage.py makemigrations --check` — sin cambios de
      modelo necesarios (no se modifican modelos existentes).
