# Electronic Signature Service — Specification

## ADDED Requirements

### Requirement: Electronic Signer Service Interface

The system SHALL provide an abstract `ElectronicSigner` service with a `sign(document_data: bytes) -> SignatureResult` method that returns the signed document hash and metadata.

#### Scenario: Sign document with SHA-256 hash
- **WHEN** the signer service receives document bytes
- **THEN** it SHALL return a `SignatureResult` containing:
  - `pre_sign_hash`: SHA-256 hash before signing
  - `post_sign_hash`: SHA-256 hash after signing
  - `signature_metadata`: JSON with provider, timestamp, algorithm

#### Scenario: Mock provider returns consistent results in development
- **WHEN** the environment is "development"
- **THEN** the signer SHALL use `MockSigner` that returns deterministic hashes for reproducibility

### Requirement: Document Integrity Verification

The system SHALL provide a `verify(document_data: bytes, expected_hash: str) -> bool` method that compares the computed SHA-256 hash against the expected hash.

#### Scenario: Verify document integrity with matching hash
- **WHEN** `verify()` is called with document data and its expected SHA-256 hash
- **THEN** it SHALL return `True` if hashes match

#### Scenario: Verify document integrity with mismatching hash
- **WHEN** `verify()` is called with document data and a different SHA-256 hash than computed
- **THEN** it SHALL return `False`

### Requirement: Signature Audit Trail

The system SHALL record every signature operation in the audit log (CAP-022) with:
- Document type reference
- Pre-sign and post-sign hashes
- Timestamp (UTC)
- Provider identifier

#### Scenario: Audit log entry created on sign
- **WHEN** `sign()` is called
- **THEN** an audit event SHALL be created with action "ELECTRONIC_SIGNATURE" containing the signature metadata

### Requirement: Provider Interchangeability

The signer service SHALL support multiple providers through a factory pattern, allowing runtime selection without code changes.

#### Scenario: Factory returns correct provider by name
- **WHEN** `SignerFactory.get_provider("mock")` is called
- **THEN** it SHALL return a `MockSigner` instance

#### Scenario: Factory returns default provider
- **WHEN** `SignerFactory.get_provider()` is called without arguments
- **THEN** it SHALL return the default provider configured in settings
