# Tasks — CHG-301 Servicio abstracto de firma electrónica

> Referencia: `proposal.md`. Plantilla según `AGENTS.md §4`.

## 1. Implementación `LocalSigner`

- [ ] Agregar `LocalSigner` en `apps/legalization/signer.py`:
  - [ ] Hereda de `ElectronicSigner`.
  - [ ] `sign()` produce `SignatureResult` con `provider="local"`,
        `metadata["environment"] = "production"`,
        `metadata["algorithm"] = "SHA-256-RFC6234"` (compatible con
        Decreto 0372/2025 Art. 45).
  - [ ] `verify()` compara `sha256(document_data)` con
        `expected_hash` (mismo algoritmo que `MockSigner`).
- [ ] Registrar `LocalSigner` en `SignerFactory._providers`
  con nombre `"local"`.

## 2. Setting de provider

- [ ] Agregar en `config/settings.py` (cerca de otras settings de
      apps):
  ```python
  # CHG-301 — Electronic signature provider.
  # "mock" only for dev/tests; staging/prod MUST use "local".
  SIGNATURE_PROVIDER = env("SIGNATURE_PROVIDER", default="mock")
  ```

## 3. Helper `sign_legal_document`

- [ ] Agregar en `apps/legalization/services.py`:
  - [ ] `sign_legal_document(document: LegalDocument, actor=None) ->
        SignatureResult`:
    - [ ] Lee `document.pdf` (raises si vacío).
    - [ ] Si `document.post_sign_hash` ya está seteado → idempotent:
          retorna el `SignatureResult` cacheado o regenera con el
          mismo contenido (mismo hash).
    - [ ] Llama `SignerFactory.get_provider().sign(pdf_bytes)`.
    - [ ] Persiste `pre_sign_hash`, `post_sign_hash`,
          `signed_at = timezone.now()`.
    - [ ] Persiste metadata en `document.changes` (JSONField).
    - [ ] Registra audit event (CHG-801) `ELECTRONIC_SIGNATURE`.
    - [ ] Retorna el `SignatureResult`.

## 4. Tests del signer

- [ ] Crear `apps/legalization/tests/__init__.py` (paquete).
- [ ] Crear `apps/legalization/tests/test_signer.py`:
  - [ ] `test_mock_signer_is_deterministic` — sign(b"x") produce
        mismo hash en N corridas.
  - [ ] `test_local_signer_is_deterministic` — idem para LocalSigner.
  - [ ] `test_sign_returns_consistent_pre_hash` — pre_hash ==
        sha256(document).
  - [ ] `test_post_hash_differs_from_pre_hash` — pre_hash !=
        post_hash (siempre que el documento no esté vacío).
  - [ ] `test_verify_after_sign_returns_true` — roundtrip
        sign → verify con pre_hash.
  - [ ] `test_verify_with_modified_document_returns_false` —
        mutar el documento → verify False.
  - [ ] `test_factory_returns_mock_by_default` — sin config
        explícita, retorna MockSigner.
  - [ ] `test_factory_returns_local_by_name` — get_provider("local")
        retorna LocalSigner.
  - [ ] `test_factory_unknown_raises` — ValueError.
  - [ ] `test_sign_legal_document_persists_hashes` — pre_sign_hash
        y post_sign_hash quedan en `document.pre_sign_hash` /
        `document.post_sign_hash`.
  - [ ] `test_sign_legal_document_is_idempotent` — segunda llamada
        no cambia `signed_at` ni `post_sign_hash`.
  - [ ] `test_sign_legal_document_logs_audit_event` — verifica
        que se creó un `AuditEvent` con `action="ELECTRONIC_SIGNATURE"`.

## 5. Spec delta

- [ ] Crear `openspec/changes/CHG-301-e-signature/specs/legalization/spec.md`
      con bloques `## ADDED` para: implementaciones del signer,
      setting configurable, helper `sign_legal_document`, garantía
      de idempotencia.

## 6. Documentación

- [ ] Crear `docs/legalization/signer.md` cubriendo:
  - [ ] Configuración del provider (`SIGNATURE_PROVIDER=mock|local`).
  - [ ] Contrato del ABC (`sign`, `verify`).
  - [ ] Garantías criptográficas (SHA-256, HMAC).
  - [ ] Cómo verificar una firma registrada manualmente.
  - [ ] Diferencia entre Mock y Local (solo metadata).

## 7. Verificación final

- [ ] `python -c "import ast; ast.parse(open('apps/legalization/signer.py').read()); ast.parse(open('apps/legalization/services.py').read())"`.
- [ ] `python -m pytest apps/legalization/tests/test_signer.py --no-header -q`.
- [ ] `python manage.py check` no reporta errores.

## 8. Hand-off

- [ ] Escribir `openspec/changes/CHG-301-e-signature/apply-progress.md`
      con resumen, archivos tocados, comandos de verificación y
      resultados.
