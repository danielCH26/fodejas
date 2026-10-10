## Context

La Fase 3 requiere que los beneficiarios firmen electrónicamente documentos legales (pagaré, carta de instrucciones, contrato). El Decreto 0372/2025 y el CPACA exigen integridad y trazabilidad de estos documentos. Actualmente no existe un servicio centralizado de firma electrónica.

## Goals / Non-Goals

**Goals:**
- Crear servicio abstracto de firma electrónica con interfaz intercambiable
- Implementar hash SHA-256 para verificar integridad de documentos
- Registrar eventos de firma en auditoría (CAP-022)
- Soportar múltiples proveedores de firma (mock para dev, producción diferido)

**Non-Goals:**
- Integración con proveedor de firma específico (e.firma, DocuSign, etc.)
- Firma de documentos PDF nativa (se usará hash + referencia)
- Validación de identidad del firmante (externo al sistema)

## Decisions

### D1: Servicio Abstracto con Implementación Intercambiable

Se implementará un servicio abstracto (`ElectronicSigner`) con método `sign(document_bytes) -> SignatureResult`. Esto permite:
- Desarrollo con mock sin dependencia externa
- Cambiar proveedor sin modificar código de documentos
- Testing unitario con mocks

**Alternativa descartada**: Integración directa en cada modelo de documento → Acoplamiento alto, difícil testing.

### D2: Hash SHA-256 para Integridad

Se usa SHA-256 porque:
- Requerido por el Art. 45 CPACA para actos administrativos
- Disponible en biblioteca estándar Python (`hashlib`)
- Suficiente para verificación de integridad

**Alternativa descartada**: Firma digital con clave asimétrica → Requiere infraestructura PKI que no está en scope.

### D3: Modelo de Auditoría de Firmas

Cada operación de firma registrará:
- Hash previo del documento
- Hash posterior (post-firma)
- Timestamp UTC
- Identificador del proveedor usado
- Referencia al documento firmado

## Risks / Trade-offs

- [Risk] Proveedor de firma externo no disponible → Mitigation: Implementación mock permite desarrollo offline
- [Risk] Documento modificado después de firma → Mitigation: Hash post-firma permite detección; warn si no coincide
- [Risk] Retención de documentos firmados (20 años según normativo) → Mitigation: Storage S3 con lifecycle policy

## Migration Plan

1. Crear app `apps/legalization/`
2. Implementar `signer.py` con interfaz abstracta
3. Crear migración de modelos
4. Integrar con auditoría existente
5. No hay rollback necesario (estructura nueva)
