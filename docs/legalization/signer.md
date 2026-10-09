# Signer de firma electrónica (CAP-029, CHG-301)

> Documento operativo. Referencia:
> `openspec/changes/CHG-301-e-signature/proposal.md`.

## Configuración

`SIGNATURE_PROVIDER` (Django setting, default `mock`):

- `dev`: `mock`. Trazas deterministas; tests pasan con esto.
- `staging` / `prod`: `local`. HMAC-SHA256 con metadata
  `environment=production`.

```bash
# .env (staging):
SIGNATURE_PROVIDER=local
```

```python
# config/settings.py
SIGNATURE_PROVIDER = env("SIGNATURE_PROVIDER", default="mock")
```

## Implementaciones registradas

`SignerFactory._providers`:

| Nombre | Uso | Metadata |
|--------|-----|----------|
| `mock` | dev, tests | `environment=development`, `algorithm=SHA-256` |
| `local` | staging, prod | `environment=production`, `algorithm=SHA-256-RFC6234` |

Ambos usan el mismo primitive criptográfico: `sha256(document_data + signature_blob)`. La diferencia es solo metadata.

## Garantías criptográficas

- **Determinismo**: mismo input + mismo provider → mismo `pre_sign_hash` y mismo `post_sign_hash`. Ver `apps/legalization/tests/test_signer.py::TestSignerAlgorithms::test_*_is_deterministic`.
- **Hash de documento**: `pre_sign_hash = sha256(document_bytes).hexdigest()` (64 hex chars).
- **Hash post-firma**: `post_sign_hash = sha256(document_bytes + signature_blob).hexdigest()` donde `signature_blob = json.dumps(metadata, sort_keys=True).encode()`.
- **Verificación**: `verify(document_bytes, expected_hash)` compara `sha256(document_bytes)` con `expected_hash` (no requiere metadata).
- **Idempotencia del helper**: `sign_legal_document(doc)` es no-op en llamadas repetidas con el mismo PDF. El `signed_at` y `post_sign_hash` no cambian; no se crea un audit event duplicado.

## Cómo firmar un documento

```python
from apps.legalization.services import sign_legal_document

result = sign_legal_document(legal_document, actor=request.user)
# result.pre_sign_hash, result.post_sign_hash, result.metadata, result.provider
```

Internamente:
1. Lee `legal_document.pdf` (raise `ValueError` si está vacío).
2. Compara `pre_hash` actual con `sha256(pdf_bytes)`. Si coincide con
   el `pre_sign_hash` ya persistido Y el documento ya tiene
   `post_sign_hash`, retorna el `SignatureResult` cacheado sin
   re-firmar (idempotente).
3. Si no, llama `SignerFactory.get_provider().sign(pdf_bytes)`.
4. Persiste `pre_sign_hash`, `post_sign_hash`, `signed_at`, metadata.
5. Registra audit event `ELECTRONIC_SIGNATURE` en
   `apps/audit/services.py:log_audit_event()`.

## Cómo verificar manualmente una firma registrada

```python
from apps.legalization.signer import verify_document

# En el admin o un shell:
with legal_document.pdf.open("rb") as f:
    pdf_bytes = f.read()

assert verify_document(pdf_bytes, legal_document.pre_sign_hash)
# Si retorna False, el PDF fue modificado después de la firma.
```

## Diferencia entre MockSigner y LocalSigner

| Aspecto | MockSigner | LocalSigner |
|---------|-----------|------------|
| Primitive | HMAC-SHA256 | HMAC-SHA256 (idéntico) |
| `provider` | `"mock"` | `"local"` |
| `metadata["environment"]` | `"development"` | `"production"` |
| `metadata["algorithm"]` | `"SHA-256"` | `"SHA-256-RFC6234"` |
| Uso | dev, tests | staging, prod |

El primitive criptográfico es idéntico — la elección entre Mock y Local es operacional (qué metadata se registra), no de seguridad.

## Anti-patterns

- **NO** configurar `SIGNATURE_PROVIDER=mock` en staging o producción. Hacerlo deja `metadata["environment"] = "development"` en cada firma, lo que rompe auditoría.
- **NO** modificar el PDF después de firmar. El `pre_sign_hash` se calcula sobre los bytes del PDF al momento de la firma; cualquier modificación invalida el hash.
- **NO** pasar un PDF vacío a `sign_legal_document`. La función raise `ValueError` con mensaje explícito.

## Integración con CHG-802 (Celery) y CHG-801 (Audit)

- `sign_legal_document` registra cada firma exitosa en
  `AuditEvent` (acción `ELECTRONIC_SIGNATURE`, módulo
  `legalization`). Esto da trazabilidad inmutable per CAP-022.
- Las tareas Celery que invocan el signer (futuro, CHG-302) deben
  usar `sign_legal_document` directamente para mantener la
  idempotencia y el audit logging consistente.
