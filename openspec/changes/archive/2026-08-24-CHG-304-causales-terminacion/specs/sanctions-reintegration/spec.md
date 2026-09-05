## ADDED Requirements

### Requirement: Sanction creation
The system SHALL create sanctions for reimbursement when termination cause is adulteración or información falsa per Art. 17 Decreto 0372/2025.

#### Scenario: Auto-create sanction for fraud
- **WHEN** termination cause is adulteración or información falsa
- **THEN** system SHALL automatically create a sanction with full reimbursement amount

### Requirement: Reimbursement calculation
The system SHALL calculate reimbursement amount including original value plus IPC adjustment.

#### Scenario: Calculate IPC adjustment
- **WHEN** calculating reimbursement amount
- **THEN** system SHALL add annual IPC percentage to base amount

### Requirement: Justification for exception
The system SHALL accept only valid justifications per Art. 17: enfermedad grave certificada, accidente con afectación significativa, emergencia familiar, traslado definitivo fuera del país.

#### Scenario: Submit justification
- **WHEN** user submits justification for exception
- **THEN** system SHALL validate justification is in approved list

#### Scenario: Approve justification
- **WHEN** admin reviews and approves justification
- **THEN** sanction status changes to CONDONADA and payment obligation is waived

### Requirement: Appeal process
The system SHALL support appeals to Oficina Jurídica per Art. 17.

#### Scenario: File appeal
- **WHEN** user files appeal for sanction
- **THEN** system creates linked appeal in claims app with SANCIÓN reference

### Requirement: Death termination
The system SHALL automatically condone all sanctions when beneficiary dies.

#### Scenario: Death reported
- **WHEN** termination cause is muerte
- **THEN** all active sanctions SHALL be automatically marked as CONDONADA
