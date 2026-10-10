# Tasks — CHG-301 Servicio abstracto de firma electrónica

> Referencia: `proposal.md`. Plantilla según `AGENTS.md §4`.

## 1. Implementación `LocalSigner`

- [x] Agregar `LocalSigner` en `apps/legalization/signer.py`:
  - [x] Hereda de `ElectronicSigner`.
  - [x] `sign()` produce `SignatureResult` con `provider="local"`,
        `metadata["environment"] = "production"`,
        `metadata["algorithm"] = "SHA-256-RFC6234"` (compatible con
        Decreto 0372/2025 Art. 45).
  - [x] `verify()` compara `sha256(document_data)` con
        `expected_hash` (mismo algoritmo que `MockSigner`).
- [x] Registrar `LocalSigner` en `SignerFactory._providers`
  con nombre `"local"`.

## 2. Setting de provider

- [x] `SIGNATURE_PROVIDER` ya existe en `config/settings.py`
      (confirmado por parent; no se requiere cambio).

## 3. Helper `sign_legal_document`

- [x] Implementado en `apps/legalization/services.py`:
  - [x] Lee `document.pdf` (raises ValueError si vacío).
  - [x] Si `document.post_sign_hash` ya está seteado → idempotent:
        retorna el `SignatureResult` cacheado sin re-firmar.
  - [x] Llama `SignerFactory.get_provider().sign(pdf_bytes)`.
  - [x] Persiste `pre_sign_hash`, `post_sign_hash`,
        `signed_at = timezone.now()`.
  - [x] Persiste metadata en `document.changes` (JSONField).
  - [x] Registra audit event (CHG-801) `ELECTRONIC_SIGNATURE`.
  - [x] Retorna el `SignatureResult`.

## 4. Tests del signer

- [x] `apps/legalization/tests/__init__.py` (paquete) — ya existe.
- [x] `apps/legalization/tests/test_signer.py` (20 tests):
  - [x] `test_mock_signer_is_deterministic` — sign(b"x") produce
        mismo pre_hash y post_hash en N corridas.
  - [x] `test_local_signer_is_deterministic` — idem para LocalSigner.
  - [x] `test_sign_returns_consistent_pre_hash` / `test_pre_hash_matches_sha256`
        — pre_hash == sha256(document).
  - [x] `test_post_hash_differs_from_pre_hash` — pre_hash != post_hash.
  - [x] `test_verify_after_sign_returns_true` — roundtrip
        sign → verify con pre_hash.
  - [x] `test_verify_with_modified_document_returns_false` —
        mutar el documento → verify False.
  - [x] `test_factory_returns_mock_by_default` — sin config
        explícita, retorna MockSigner.
  - [x] `test_factory_returns_local_by_name` — get_provider("local")
        retorna LocalSigner.
  - [x] `test_factory_unknown_raises` — ValueError.
  - [x] `test_sign_legal_document_persists_hashes` — pre_sign_hash
        y post_sign_hash quedan en el documento.
  - [x] `test_sign_legal_document_is_idempotent` — segunda llamada
        no cambia `signed_at` ni `post_sign_hash`.
  - [x] `test_sign_legal_document_logs_audit_event` — verifica
        que se creó un `AuditEvent` con `action="ELECTRONIC_SIGNATURE"`.
  - [x] `test_idempotent_does_not_create_duplicate_audit_event`
  - [x] `test_empty_pdf_raises`
  - [x] `test_convenience_sign_document_helper`
  - [x] `test_convenience_verify_document_helper`

## 5. Spec delta

- [x] `openspec/changes/CHG-301-e-signature/specs/legalization/spec.md`
      creado con bloques `## ADDED` para: implementaciones del signer,
      setting configurable, helper `sign_legal_document`, garantía
      de idempotencia.

## 6. Documentación

- [x] `docs/legalization/signer.md` creado cubriendo:
  - [x] Configuración del provider (`SIGNATURE_PROVIDER=mock|local`).
  - [x] Contrato del ABC (`sign`, `verify`).
  - [x] Garantías criptográficas (SHA-256, HMAC).
  - [x] Cómo verificar una firma registrada manualmente.
  - [x] Diferencia entre Mock y Local (solo metadata).

## 7. Verificación final

- [x] AST parse de `signer.py` y `services.py` → sin errores de sintaxis.
- [x] `pytest apps/legalization/tests/test_signer.py -q` → 20 passed.
- [x] `python manage.py check` → 0 issues.

## 8. Hand-off

- [x] `apply-progress.md` — deferred to batch final (BATCH 3 o CHG-302).

## Batch notes

### BATCH 1 — signer core (esta tanda)

Completado en commits:
- `fix(CHG-301): document.uuid → document.id in sign_legal_document`
- `fix(CHG-301): make MockSigner and LocalSigner fully deterministic`
- `feat(CHG-301): add changes JSONField to LegalDocument`
- `fix(CHG-301): correct test assertions in test_signer.py`

Correcciones adicionales descubiertas durante implementación:
- `document.uuid` apareció en **4** sitios (no 3): error message,
  `entity_id` en audit call, `changes` dict, y log message.
- `LegalDocument` no tenía campo `changes` → creado migration
  `0002_add_changes_field.py`.
- `MockSigner.sign()` usaba `datetime.now()` en el signature blob,
  haciendo `post_sign_hash` no-determinístico. Corregido con epoch
  fijo (2000-01-01 UTC) en el blob; timestamp real en metadata.
- `AuditEvent.entity_id` es `UUIDField` → test assertion usa UUID,
  no string.

Tests: 20 passed (requires `--create-db` para forzar schema fresco;
esto es una limitación del conftest ephemeral-in-memory sqlite).

### BATCH 2 — vistas, URLs, flujos, admin

Completado en commits:
- `feat(CHG-301): add DRF API for document sign/verify (CAP-029)`
- `feat(CHG-301): add HTMX signing views and lean partial templates (CAP-029)`
- `fix(CHG-301): add Django admin for LegalDocument/Process (CAP-029)`
- `feat(CHG-301): wire legalization URLs into config/urls.py and add check_signer_config management command (CAP-029)`

Completado:
- [x] Endpoints DRF: POST /api/legalization/documents/<pk>/sign/,
      GET /api/legalization/documents/<pk>/verify/,
      GET /api/legalization/processes/
- [x] Permisos: R-JUNTA/R-ADMIN ven todos los docs; Aspirantes
      solo los suyos
- [x] Vistas HTMX: LegalizationListView, LegalizationDetailView,
      SignDocumentHTMXView con hx-get/hx-post
- [x] Templates: base.html, list.html, detail.html + partials/
      (sign_form.html, document_row.html)
- [x] URLs: /legalization/ y /api/legalization/ en config/urls.py
- [x] Admin: LegalDocumentAdmin con HashFields de solo lectura,
      LegalizationProcessAdmin
- [x] Management command: check_signer_config (exits non-zero si
      SIGNATURE_PROVIDER=mock en staging/prod)
- [x] Tests: 14 API tests + 7 management command tests = 21 nuevos
- [x] Verificación e2e: test_e2e_create_sign_verify_audit_flow
      (proceso → sign → verify → audit event → idempotency)

Deferred:
- [ ] WeasyPrint template de documento legal (CHG-302)
- [ ] Celery async signing (CHG-302 — no se necesita para MVP;
      hash chain integrity es más simple con signing síncrono)
- [ ] `apply-progress.md` — batch final o CHG-302

Tests totales: 41 passed (20 test_signer.py + 14 test_api.py +
7 test_management.py).

### Desviaciones de la tarea original

1. Campo `changes` no existía en el modelo → se creó
   `0002_add_changes_field.py`. La tarea §3 mencionaba el campo
   pero no se especificó cómo crearlo.
2. Tests requieren `--create-db` en el runner de pytest debido al
   conftest ephemeral-in-memory sqlite que no detecta cambios de
   schema entre sesiones sin flag. Esto es una limitación ambiental,
   no de código.
3. `.atl/` files muestran line-ending noise en git diff (CRLF/LF)
   — no son cambios de esta tanda; el parent puede excluirlos.
