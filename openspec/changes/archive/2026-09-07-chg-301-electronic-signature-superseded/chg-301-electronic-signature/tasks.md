# Tasks — CHG-301 Electronic Signature

## 1. Setup

- [ ] 1.1 Create Django app `apps/legalization/` with standard structure
- [ ] 1.2 Add `apps/legalization` to `INSTALLED_APPS` in settings
- [ ] 1.3 Configure signing provider in settings (default: mock)

## 2. Electronic Signer Service

- [ ] 2.1 Create `apps/legalization/signer.py` with abstract `ElectronicSigner` base class
- [ ] 2.2 Implement `SignatureResult` dataclass with pre_sign_hash, post_sign_hash, metadata
- [ ] 2.3 Create `MockSigner` implementation for development
- [ ] 2.4 Implement `SignerFactory` with `get_provider()` method
- [ ] 2.5 Add `sign()` method with SHA-256 hashing
- [ ] 2.6 Add `verify()` method for integrity checks

## 3. Integration with Audit

- [ ] 3.1 Import audit service in signer module
- [ ] 3.2 Add audit log call on every `sign()` operation
- [ ] 3.3 Register "ELECTRONIC_SIGNATURE" action in audit

## 4. Models and Migrations

- [ ] 4.1 Create `apps/legalization/models.py` with DocumentSignature model (optional, for tracking)
- [ ] 4.2 Generate and run initial migration
- [ ] 4.3 Register models in admin (optional)

## 5. Tests

- [ ] 5.1 Write unit tests for `MockSigner.sign()`
- [ ] 5.2 Write unit tests for `MockSigner.verify()`
- [ ] 5.3 Write test for `SignerFactory.get_provider()`
- [ ] 5.4 Write integration test for audit logging on sign

## 6. Documentation

- [ ] 6.1 Add docstrings to signer classes following Google style
- [ ] 6.2 Document usage in README or internal docs
