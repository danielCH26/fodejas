## Why

Una vez legalizado el crédito (CHG-302), los beneficiarios deben recibir sus desembolsos. El Decreto 0372/2025 exige autorización del Presidente de la Junta Administradora y el Secretario de Educación, con orden radicada en Tesorería. La plataforma debe gestionar este flujo y mantener trazabilidad.

## What Changes

- Crear modelo para autorización de pagos (DesbursementAuthorization)
- Workflow: pendiente → autorizado (firma) → ordenado a Tesorería → pagado
- Integración conlegalization para verificar documentos legalizados
- Vista de conciliación manual para Tesorería
- Registro en auditoría (CAP-022)

## Capabilities

### New Capabilities
- **disbursement**: Gestión de autorización de pagos y órdenes a Tesorería

### Modified Capabilities
- Ninguno

## Impact

- Nueva funcionalidad en: `apps/treasury/`
- Depende de: CHG-302 (legalización), CHG-301 (firma electrónica)
- Afecta: CHG-304 (causales de terminación)
