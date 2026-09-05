## Why

La Fase 3 (Legalización y Pagos) requiere que los beneficiarios firmen electrónicamente el pagaré, la carta de instrucciones y el contrato. Sin un servicio de firma electrónica abstracto, cada documento implementará su propia lógica de firma, dificultando el mantenimiento y la auditoría. Además, el Art. 45 del CPACA y el Decreto 0372/2025 exigen trazabilidad integridad documental.

## What Changes

- Crear servicio abstracto de firma electrónica (`apps/legalization/signer.py`) con implementación interchangeable
- Implementar hash SHA-256 para integridad de documentos firmados
- Crear modelo de auditoría de firmas con hash previo y posterior
- Definir interfaz para proveedores de firma (mock para desarrollo, implementación real diferida)
- Integrar con el modelo de documentos de legalización

## Capabilities

### New Capabilities
- **electronic-signature**: Servicio abstracto de firma electrónica con hash SHA-256 para documentos de legalización

### Modified Capabilities
- Ninguno (CAP-029 es capacidad nueva)

## Impact

- Nueva app: `apps/legalization/`
- Afecta: CHG-302 (legalización), CHG-303 (desembolsos)
- Dependencias: CAP-022 (auditoría) para registrar eventos de firma
