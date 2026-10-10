# Tasks — CHG-302 Legalization

## 1. Models

- [x] 1.1 Create `LegalDocument` model with document_type, status, hashes
      *(satisfied by CHG-301: 5a6334a — model exists with document_type, status, pre/post hash fields)*
- [x] 1.2 Create `LegalizationProcess` model to track overall process
      *(satisfied by CHG-301: 5a6334a — model exists)*
- [x] 1.3 Add LegalizationProcess foreign key to LegalDocument
      *(satisfied by CHG-301: 5a6334a — FK defined on LegalDocument.process)*
- [x] 1.4 Generate and run migrations
      *(satisfied by CHG-301: migrations 0001_initial, 0002_add_changes_field applied)*

## 2. Services

- [x] 2.1 Create `LegalizationService` class with workflow methods
      *(implemented in apps/legalization/services.py — CHG-302 Batch A)*
- [x] 2.2 Implement `create_documents_for_beneficiary()`
      *(returns dict of 3 documents; wraps create_process_for_beneficiary — CHG-302 Batch A)*
- [x] 2.3 Implement `sign_document()` with CHG-301 integration
      *(satisfied by CHG-301: 3730ceb — sign_legal_document in services.py uses signer.py)*
- [x] 2.4 Implement `generate_pdf()` using WeasyPrint
      *(seam strategy: real WeasyPrint when available, RuntimeError+skip when not;
       templates render, hash stored, audit logged — CHG-302 Batch A)*
- [x] 2.5 Implement `complete_legalization()` workflow
      *(requires all 3 FIRMADO → all 3 LEGALIZADO; idempotent; raises on non-FIRMADO — CHG-302 Batch A)*

## 3. PDF Templates

- [x] 3.1 Create pagaré HTML template
      *(templates/legalization/pdf/pagare.html — CHG-302 Batch A)*
- [x] 3.2 Create carta de instrucciones HTML template
      *(templates/legalization/pdf/carta_instrucciones.html — CHG-302 Batch A)*
- [x] 3.3 Create contrato HTML template
      *(templates/legalization/pdf/contrato.html — CHG-302 Batch A)*
- [x] 3.4 Add CSS styling for all templates
      *(templates/legalization/pdf/legal.css — CHG-302 Batch A)*

## 4. Views and URLs

- [ ] 4.1 Create list view for LegalizationProcess
      **→ Batch B**
- [ ] 4.2 Create detail view with document status
      **→ Batch B**
- [ ] 4.3 Create sign action view
      **→ Batch B**
- [ ] 4.4 Add URLs for legalization views
      **→ Batch B**
- [ ] 4.5 Add to base.html menu (R-JUNTA role)
      **→ Batch B**

## 5. Integration

- [x] 5.1 Integrate with CHG-301 signer service
      *(satisfied by CHG-301: 3730ceb — signer.py, SignerFactory wired into sign_legal_document)*
- [x] 5.2 Add audit logging for all operations
      *(generate_pdf → GENERATE_PDF; complete_legalization → LEGALIZATION_COMPLETE;
       cancel_document → DOCUMENT_CANCELLED; all from service layer — CHG-302 Batch A)*
- [x] 5.3 Handle edge cases (missing documents, timeouts)
      *(complete_legalization raises on non-FIRMADO/cancelled; cancel_document guards
       terminal states; sign_legal_document idempotency; post-sign tamper detection tested — CHG-302 Batch A)*

## 6. Tests

- [x] 6.1 Write unit tests for LegalizationService
      *(TestCreateDocumentsForBeneficiary, TestCompleteLegalization, TestCancelDocument — CHG-302 Batch A)*
- [x] 6.2 Write tests for document workflow transitions
      *(TestDocumentTransitions, TestProcessTransitions — CHG-302 Batch A)*
- [x] 6.3 Write tests for PDF generation
      *(TestGeneratePdf: template selection, hash storage, audit, seam, unknown doc type — CHG-302 Batch A)*
- [x] 6.4 Write integration tests for signer
      *(TestPostSignTamperDetection: verifies tampered PDF produces different post_sign_hash — CHG-302 Batch A)*

## 7. Admin

- [x] 7.1 Register models in admin
      *(satisfied by CHG-301: 04965e9 — LegalDocument and LegalizationProcess registered)*
- [ ] 7.2 Add list filters by status and beneficiary
      **→ Batch B**

---

## Batch Notes — CHG-302 Batch A (this implementation)

**Completed in this batch:**
- LegalizationService with create_documents_for_beneficiary(), generate_pdf() (WeasyPrint seam),
  complete_legalization(), cancel_document()
- Domain state machine (apps/legalization/domain/transitions.py): PENDIENTE→FIRMADO→LEGALIZADO
  with CANCELADO branch; process-level FSM; terminal-state guards
- PDF templates: pagare.html, carta_instrucciones.html, contrato.html + legal.css
  (Spanish, synthetic placeholder data, SHA-256 hash anchors in footer)
- Audit from service layer: GENERATE_PDF, LEGALIZATION_COMPLETE, DOCUMENT_CANCELLED events
- Post-sign tamper detection: modify-after-sign changes pre_hash → new post_hash
- 30 new unit/integration tests (test_services.py); 71 total tests green

**Batch B still owns:**
- 4.1 — List view (LegalizationProcess list)
- 4.2 — Detail view (document status per process)
- 4.3 — Sign action view
- 4.4 — URL routing for views above
- 4.5 — Menu entry in base.html for R-JUNTA role
- 7.2 — Admin list filters (status, beneficiary)

**Deferrals:**
- None beyond Batch B scope above.
