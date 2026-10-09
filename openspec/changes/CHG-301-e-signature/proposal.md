# CHG-301 — Servicio abstracto de firma electrónica (CAP-029)

## Contexto

`roadmap.md §7.1` requiere para CAP-029:
> "Servicio abstracto de firma electrónica + hash SHA-256"
> Aplicación: `apps/legalization/`

`apps/legalization/signer.py` ya tiene implementada la mayor parte
de la base: `ElectronicSigner` (ABC), `MockSigner`,
`SignerFactory`, y los helpers `sign_document()` /
`verify_document()` que se integran con el audit signal CHG-801.

Pero el change está incompleto para producción:

- Solo existe `MockSigner`. Para staging y producción se necesita
  un `LocalSigner` que use el mismo primitive criptográfico
  (HMAC-SHA256 sobre el contenido del documento + metadata de
  firma) pero con metadata explícita de producción
  (`environment=production`, `algorithm=SHA-256-RFC6234`-compatible,
  no `mock`).
- Cero tests del módulo `signer.py`. Sin tests, no se puede
  verificar la integridad criptográfica ni el contrato del ABC.
- No hay helper que vincule `LegalDocument.sign()` con el signer.
  Hoy la firma se hace "ad-hoc" desde las vistas, saltando el
  helper.
- Sin documentación operativa del signer: cómo se configura el
  provider, qué guarantees da, cómo se verifica una firma
  registrada.

Per `AGENTS.md §6 regla 2` no se integran proveedores externos de
firma (no DocuSign, no Certicámara, no AWS Signer). El signer es
**interno** y usa cryptography local. Esto es deliberado: el
Decreto 0372/2025 no exige un proveedor certificado, exige
**integridad verificable** (hash SHA-256 + metadata de firma).

## Capacidades afectadas

- **CAP-029** (Servicio abstracto de firma electrónica + hash
  SHA-256, `project.md §8`). Materializa CHG-301.

## Reglas de negocio afectadas

- `AGENTS.md §6` regla 2 (sin integraciones externas; signer local).
- `roadmap.md §7.2` entregable verificable: "Un beneficiario puede
  firmar electrónicamente pagaré, carta de instrucciones y contrato;
  los documentos se almacenan con hash SHA-256".
- Decreto 0372/2025 (Art. 45 sobre integridad documental vía hash).

## Cambios propuestos

### Delta en `specs/legalization/spec.md` (nuevo spec)

#### ADDED — § Implementación local de firma

`ElectronicSigner` SHALL tener al menos dos implementaciones
registradas en `SignerFactory`:

- `MockSigner` — para development y tests. Metadata
  `environment=development`. NO SHALL usarse en staging ni
  producción.
- `LocalSigner` — para staging y producción. Metadata
  `environment=production`. Usa el mismo primitive
  HMAC-SHA256 que `MockSigner`; la diferencia es metadata y
  configuración, no el algoritmo criptográfico.

#### ADDED — § Provider configurable vía settings

`SIGNATURE_PROVIDER` (Django setting, default `mock`) SHALL
seleccionar el provider usado por `SignerFactory.get_provider()`.
En staging y producción SHALL estar configurado como `local`. En
tests SHALL estar configurado como `mock`.

#### ADDED — § Helper `LegalDocument.sign_with_signer()`

`LegalDocument.sign_with_signer(actor=None)` SHALL:
1. Leer el contenido del PDF (`self.pdf`).
2. Calcular `pre_sign_hash = sha256(pdf_bytes)`.
3. Llamar `SignerFactory.get_provider().sign(pdf_bytes)` para
   obtener `post_sign_hash` y metadata.
4. Persistir `pre_sign_hash`, `post_sign_hash`, `signed_at =
   timezone.now()`, y metadata en `self.changes`.
5. Registrar evento en el audit log (CAP-022 vía CHG-801).

#### ADDED — § Garantía de idempotencia

`sign_with_signer()` SHALL ser idempotente: una segunda llamada
sobre el mismo `LegalDocument` con el mismo PDF SHALL NO crear un
nuevo audit event ni modificar `post_sign_hash` (la firma ya está).
El test SHALL verificar que `signed_at` no cambia entre llamadas.

### Cambios concretos

1. `apps/legalization/signer.py`: agregar `LocalSigner` con
   `environment=production`, sin metadata de mock. Comportamiento
   criptográfico idéntico a `MockSigner` (mismo HMAC-SHA256) — la
   diferencia es solo metadata.

2. `apps/legalization/signer.py`: actualizar `SignerFactory` para
   registrar `LocalSigner` con nombre `local`.

3. `apps/legalization/services.py`: agregar
   `sign_legal_document(document, actor=None) -> SignatureResult`
   que llama el signer configurado, valida que `document.pdf`
   existe, y persiste los hashes + metadata. Maneja el caso de
   firma duplicada (no-op si ya tiene `post_sign_hash`).

4. `apps/legalization/tests/test_signer.py` (nuevo): tests
   unitarios del signer.
   - `ElectronicSigner` (vía `MockSigner` y `LocalSigner`):
     determinismo, idempotencia, hash válido, metadata correcta.
   - `SignerFactory.get_provider("mock")` y `("local")` retornan
     instancias válidas; `("unknown")` lanza `ValueError`.
   - `sign_document()` + `verify_document()` roundtrip: dado un
     PDF simulado, `sign_document` produce `pre_sign_hash` y
     `post_sign_hash`; `verify_document` confirma que `pre_sign_hash`
     coincide.
   - `sign_legal_document()`: firma un `LegalDocument`, verifica
     que `pre_sign_hash` y `post_sign_hash` se persisten y que el
     audit log recibe el evento `ELECTRONIC_SIGNATURE`.

5. `docs/legalization/signer.md` (nuevo): documentación operativa
   del signer. Cubre: provider configuration, contrato del ABC,
   garantías criptográficas, cómo verificar una firma registrada.

## Criterios de aceptación

- [ ] `LocalSigner` existe y está registrado en `SignerFactory`.
- [ ] `SignerFactory.get_provider("local").sign(b"x")` retorna
      `SignatureResult` con `provider="local"` y
      `metadata["environment"] == "production"`.
- [ ] `SignerFactory.get_provider("unknown")` lanza `ValueError`.
- [ ] `sign_document(b"x")` produce `pre_sign_hash == sha256("x")`.
- [ ] `verify_document(b"x", pre_sign_hash) == True`.
- [ ] `sign_legal_document(doc)` persiste hashes en `doc` y registra
      audit event.
- [ ] `sign_legal_document(doc)` segunda llamada es no-op.
- [ ] `pytest apps/legalization/tests/test_signer.py` corre limpio.
- [ ] `docs/legalization/signer.md` cubre provider, contrato y
      verificación.

## Pruebas

- Unitarias:
  - `apps/legalization/tests/test_signer.py`:
    - `test_mock_signer_is_deterministic`
    - `test_local_signer_is_deterministic`
    - `test_sign_returns_consistent_pre_hash`
    - `test_post_hash_differs_from_pre_hash`
    - `test_verify_after_sign_returns_true`
    - `test_factory_returns_mock_by_default`
    - `test_factory_returns_local_by_name`
    - `test_factory_unknown_raises`
    - `test_sign_legal_document_persists_hashes`
    - `test_sign_legal_document_is_idempotent`
    - `test_sign_legal_document_logs_audit_event`

## Riesgos y Fuera del alcance

- **Riesgo**: el operador configura `SIGNATURE_PROVIDER=mock` en
  staging y no se da cuenta. Mitigación: el test suite verifica
  que en CI el provider configurado es `mock` (correcto para tests);
  agregar un management command `check_signer_config` que verifique
  en staging/prod que `SIGNATURE_PROVIDER != mock` y aborte si
  alguien lo configuró mal.
- **Riesgo**: la metadata de firma incluye timestamps naive (sin tz).
  Mitigación: usar `timezone.now()` siempre (no `datetime.now()`).
- **Fuera del alcance**:
  - No se integra con DocuSign / Certicámara / AWS Signer
    (prohibido por AGENTS.md §6 regla 2).
  - No se rediseña `LegalizationProcess` ni `LegalDocument`.
  - No se agrega PDF rendering (queda para CHG-302 legalization).

## Referencias

- `roadmap.md §7.1` y `§7.2` (CAP-029, entregables).
- `AGENTS.md §6` regla 2 (sin integraciones externas).
- Decreto 0372/2025 Art. 45 (integridad documental).
- `apps/legalization/signer.py` (base existente).
- `apps/audit/services.py` (CHG-801 audit integration).
