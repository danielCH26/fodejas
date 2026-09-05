## Why

Una vez publicado el listado definitivo (CHG-207), los beneficiarios deben legalizar su crédito mediante la firma del pagaré, carta de instrucciones y contrato. Sin un módulo de legalización, este proceso sería manual y sin trazabilidad. El Decreto 0372/2025 Art. 8 exige formalización escrita del crédito.

## What Changes

- Crear modelos para gestionar documentos de legalización (Pagaré, Carta de Instrucciones, Contrato)
- Integrar con el servicio de firma electrónica (CHG-301)
- Crear workflow de estados: pendiente → firmado → legalizado
- Generar PDFs de documentos legales usando WeasyPrint
- Registrar cada paso en auditoría (CAP-022)

## Capabilities

### New Capabilities
- **legalization**: Gestión de documentos de legalización (pagaré, carta instrucciones, contrato)

### Modified Capabilities
- Ninguno

## Impact

- Nueva funcionalidad en: `apps/legalization/`
- Depende de: CHG-301 (firma electrónica), CAP-022 (auditoría)
- Afecta: CHG-303 (desembolsos)
