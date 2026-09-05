# Legalization Service — Specification

## ADDED Requirements

### Requirement: Legal Document Model

The system SHALL provide a `LegalDocument` model to track each legal document with:
- `document_type`: Type (PAGARE, CARTA_INSTRUCCIONES, CONTRATO)
- `beneficiary`: ForeignKey to user
- `convocatoria`: ForeignKey to the call
- `status`: Workflow state (PENDIENTE, FIRMADO, LEGALIZADO, CANCELADO)
- `pre_sign_hash`: SHA-256 before signing
- `post_sign_hash`: SHA-256 after signing
- `pdf`: Generated PDF file
- `signed_at`: Timestamp when signed

#### Scenario: Create legal document for beneficiary
- **WHEN** a beneficiary is added to a definitive list
- **THEN** the system SHALL create a `LegalDocument` instance for each required document type

### Requirement: Legal Document Workflow

The system SHALL allow document status transitions:
- `firmar()`: From PENDIENTE to FIRMADO (requires signature)
- `legalizar()`: From FIRMADO to LEGALIZADO (requires all documents signed)
- `cancelar()`: From PENDIENTE to CANCELADO

#### Scenario: Sign document
- **WHEN** `firmar()` is called on a PENDIENTE document
- **THEN** the document status SHALL become FIRMADO and signature hash SHALL be stored

#### Scenario: Complete legalization
- **WHEN** all documents for a beneficiary are in FIRMADO status
- **THEN** the process status SHALL become LEGALIZADO

### Requirement: PDF Generation

The system SHALL generate PDF documents using WeasyPrint with:
- Header with FODEJAS logo and document title
- Beneficiary information
- Terms and conditions per document type
- Signature fields

#### Scenario: Generate pagaré PDF
- **WHEN** a pagaré document is created
- **THEN** the system SHALL generate a PDF with:
  - Amount in words and numbers
  - Payment terms
  - Beneficiary identification

### Requirement: Electronic Signature Integration

The system SHALL integrate with CHG-301 (ElectronicSigner) to sign documents.

#### Scenario: Sign document with electronic signature
- **WHEN** a document is signed
- **THEN** the signer service SHALL be called and hash SHALL be stored

### Requirement: Audit Trail

All document operations SHALL be logged in the audit system (CAP-022).

#### Scenario: Audit on sign
- **WHEN** a document is signed
- **THEN** an audit event SHALL be created with action "DOCUMENT_SIGNED"
