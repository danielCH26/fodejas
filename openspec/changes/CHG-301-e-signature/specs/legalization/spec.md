# Spec Delta — `legalization` (CHG-301)

> Delta para CHG-301. Bloques `## ADDED` según plantilla OpenSpec.

## ADDED

### Requirement: Implementaciones del signer

`ElectronicSigner` SHALL tener al menos dos implementaciones
registradas en `SignerFactory`:

- `MockSigner` — para development y tests. Metadata
  `environment=development`. NO SHALL usarse en staging ni
  producción.
- `LocalSigner` — para staging y producción. Metadata
  `environment=production`, `algorithm=SHA-256-RFC6234`. Usa el mismo
  primitive HMAC-SHA256 que `MockSigner`; la diferencia es solo
  metadata y configuración, no el algoritmo criptográfico.

#### Scenario: MockSigner en development

- **WHEN** `SIGNATURE_PROVIDER` está en `mock` (default en dev),
- **THEN** `SignerFactory.get_provider()` retorna una instancia de
  `MockSigner`,
- **AND** `result.metadata["environment"] == "development"`.

#### Scenario: LocalSigner en producción

- **WHEN** `SIGNATURE_PROVIDER=local` (staging o producción),
- **THEN** `SignerFactory.get_provider()` retorna una instancia de
  `LocalSigner`,
- **AND** `result.metadata["environment"] == "production"`,
- **AND** `result.metadata["algorithm"] == "SHA-256-RFC6234"`.

### Requirement: Provider configurable vía settings

`SIGNATURE_PROVIDER` (Django setting, default `mock`) SHALL
seleccionar el provider usado por `SignerFactory.get_provider()`.

- En `dev`: default `mock`. Sin configuración adicional.
- En `staging` y `prod`: SHALL estar configurado como `local`.
- En `tests`: SHALL estar configurado como `mock`.

### Requirement: Helper `sign_legal_document`

`apps.legalization.services.sign_legal_document(document, actor=None)`
SHALL:

1. Leer `document.pdf.read()`. Raises `ValueError` si está vacío.
2. Si `document.post_sign_hash` ya está seteado y el `pre_sign_hash`
   coincide con `sha256(pdf_bytes)` actual → idempotente: NO
   re-firma; retorna el `SignatureResult` con el mismo `post_sign_hash`
   pre-existente.
3. Si no → llama `SignerFactory.get_provider().sign(pdf_bytes)`.
4. Persiste `pre_sign_hash`, `post_sign_hash`, `signed_at =
   timezone.now()`, y metadata en `document.changes` (JSONField).
5. Registra evento en `AuditEvent` con `action="ELECTRONIC_SIGNATURE"`,
   `module="legalization"` (vía `apps.audit.services.log_audit_event`
   introducido en CHG-801).
6. Retorna `SignatureResult`.

### Requirement: Garantía de idempotencia

`sign_legal_document` SHALL ser idempotente sobre un
`LegalDocument` ya firmado con el mismo PDF:
- `post_sign_hash` SHALL permanecer igual.
- `signed_at` SHALL permanecer igual.
- NO SHALL crear un nuevo audit event.

#### Scenario: Segunda firma sobre el mismo documento

- **WHEN** `sign_legal_document(doc)` se llama dos veces con el mismo
      PDF,
- **THEN** la segunda llamada no modifica `doc.post_sign_hash`,
      `doc.signed_at`, ni crea un nuevo audit event.
