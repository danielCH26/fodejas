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

- [ ] `apply-progress.md` — deferred to final batch (BATCH 2 o posterior).

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

Pendientes:
- [ ] Endpoints de firma (POST /api/legalization/<id>/sign/)
- [ ] Vistas HTMX o DRF para flujo de firma
- [ ] Admin de LegalDocument y LegalizationProcess
- [ ] Template de документо firgado (WeasyPrint, CHG-302)
- [ ] Integration con Celery (CHG-302)
- [ ] Management command `check_signer_config` (riesgo de
      `SIGNATURE_PROVIDER=mock` en staging/prod)
- [ ] `apply-progress.md`
- [ ] Verificación end-to-end del flujo completo

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
