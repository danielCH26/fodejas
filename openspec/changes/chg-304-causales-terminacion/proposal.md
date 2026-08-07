## Why

CAP-015 (Terminación del Convenio y Causales) and CAP-016 (Sanciones, Reintegros y Cobro Coactivo) are P0 capabilities required to complete the scholarship lifecycle. Without termination causes and sanctions, the platform cannot handle scholarship cancellations, enforce reintegration requirements, or manage force majeure cases as mandated by Art. 14 and Art. 17 of Decreto 0372/2025.

## What Changes

- Implement termination causes for scholarship agreements (Art. 14 Decreto 0372/2025)
- Implement termination of disbursements (Art. 15 Decreto 0372/2025)
- Implement sanctions and reimbursement workflow (Art. 17 Decreto 0372/2025)
- Create models for termination requests and sanctions
- Create services for termination/sanction workflow management
- Add admin interfaces for managing terminations and sanctions

## Capabilities

### New Capabilities
- `termination-causes`: Gestión de causales de terminación de convenios (Art. 14)
- `sanctions-reintegration`: Sanciones, reintegros y cobros coactivos (Art. 17)

### Modified Capabilities
- (none)

## Impact

- **New code**: `apps/condonation/models.py`, `apps/condonation/services.py`
- **Modified code**: `apps/condonation/admin.py`, `apps/condonation/views.py`, `apps/condonation/urls.py`
- **Dependencies**: apps/legalization (for linking to legalized processes)
- **Database**: New tables for termination_requests, sanctions, reintegration_tracking
