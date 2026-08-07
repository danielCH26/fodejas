## Why

CAP-011 (Seguimiento Académico de Beneficiarios) is required after Phase 3 to track academic progress of beneficiaries. The platform needs to validate the 3.5 minimum average requirement per Art. 16 Decreto 0372/2025 and provide early alerts for at-risk beneficiaries.

## What Changes

- Implement academic tracking model for beneficiary records
- Add semester grade uploads and average calculations
- Create validation for minimum 3.5 average requirement
- Add early warning system for at-risk beneficiaries (below 3.5)
- Create alerts for academic probation and suspension triggers
- Add admin interfaces for managing academic records

## Capabilities

### New Capabilities
- `academic-tracking`: Seguimiento académico de beneficiarios con alertas tempranas

### Modified Capabilities
- (none)

## Impact

- **New code**: `apps/academic_tracking/models.py`, `apps/academic_tracking/services.py`
- **Modified code**: `apps/academic_tracking/views.py`, `apps/academic_tracking/urls.py`, `apps/academic_tracking/admin.py`
- **Dependencies**: apps/legalization (for linking to legalized processes)
- **Database**: New tables for academic records, grades, alerts
