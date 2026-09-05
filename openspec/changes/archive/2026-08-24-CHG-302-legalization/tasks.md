# Tasks — CHG-302 Legalization

## 1. Models

- [ ] 1.1 Create `LegalDocument` model with document_type, status, hashes
- [ ] 1.2 Create `LegalizationProcess` model to track overall process
- [ ] 1.3 Add LegalizationProcess foreign key to LegalDocument
- [ ] 1.4 Generate and run migrations

## 2. Services

- [ ] 2.1 Create `LegalizationService` class with workflow methods
- [ ] 2.2 Implement `create_documents_for_beneficiary()`
- [ ] 2.3 Implement `sign_document()` with CHG-301 integration
- [ ] 2.4 Implement `generate_pdf()` using WeasyPrint
- [ ] 2.5 Implement `complete_legalization()` workflow

## 3. PDF Templates

- [ ] 3.1 Create pagaré HTML template
- [ ] 3.2 Create carta de instrucciones HTML template
- [ ] 3.3 Create contrato HTML template
- [ ] 3.4 Add CSS styling for all templates

## 4. Views and URLs

- [ ] 4.1 Create list view for LegalizationProcess
- [ ] 4.2 Create detail view with document status
- [ ] 4.3 Create sign action view
- [ ] 4.4 Add URLs for legalization views
- [ ] 4.5 Add to base.html menu (R-JUNTA role)

## 5. Integration

- [ ] 5.1 Integrate with CHG-301 signer service
- [ ] 5.2 Add audit logging for all operations
- [ ] 5.3 Handle edge cases (missing documents, timeouts)

## 6. Tests

- [ ] 6.1 Write unit tests for LegalizationService
- [ ] 6.2 Write tests for document workflow transitions
- [ ] 6.3 Write tests for PDF generation
- [ ] 6.4 Write integration tests for signer

## 7. Admin

- [ ] 7.1 Register models in admin
- [ ] 7.2 Add list filters by status and beneficiary
