# Disbursement Service — Specification

## ADDED Requirements

### Requirement: Disbursement Authorization Model

The system SHALL provide a `DisbursementAuthorization` model with:
- `legalization_process`: ForeignKey to LegalizationProcess
- `amount`: Monetary value
- `status`: PENDIENTE, AUTORIZADO, ORDENADO, PAGADO, RECHAZADO
- `authorized_by_president`: User who authorized (Presidente JA)
- `authorized_by_secretary`: User who authorized (Secretario Educación)
- `authorized_at`: Timestamp of authorization
- `treasury_order_number`: Order number from Treasury
- `treasury_order_date`: Date when sent to Treasury
- `paid_at`: Date when payment was confirmed

#### Scenario: Create disbursement authorization
- **WHEN** a beneficiary's legalization is complete
- **THEN** the system SHALL create a `DisbursementAuthorization` in PENDIENTE status

### Requirement: Authorization Workflow

The system SHALL allow:
- `autorizar()`: Both authorized signatures confirm the disbursement
- `ordenar()`: Send order to Treasury
- `confirmar_pago()`: Treasury confirms payment with attached proof

#### Scenario: Authorize disbursement
- **WHEN** both Presidente JA and Secretary authorize
- **THEN** status SHALL become AUTORIZADO and timestamp recorded

### Requirement: Treasury Integration

The system SHALL provide:
- Order number generation for Treasury
- View for Treasury to confirm payment
- Attachment upload for payment proof

#### Scenario: Confirm payment
- **WHEN** Treasury confirms payment and uploads proof
- **THEN** status SHALL become PAGADO and proof attached

### Requirement: Treasury Deadline Alert

The system SHALL track the 5 business day deadline from Art. 2 Decreto 0072/2026.

#### Scenario: Treasury deadline exceeded
- **WHEN** payment not confirmed within 5 business days
- **THEN** the system SHALL send an alert notification
