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

- [x] 4.1 Create list view for LegalizationProcess
      **→ Batch B** — LegalizationListView in views.py; R-JUNTA sees all,
      beneficiaries see own. Template: templates/legalization/list.html.
      Test: test_junta_sees_all_processes, test_beneficiary_sees_only_own_process,
      test_other_aspirante_cannot_see_beneficiary_process.
- [x] 4.2 Create detail view with document status
      **→ Batch B** — LegalizationDetailView; shows process + all documents
      with status badges (Pendiente/Firmado/Legalizado/Cancelado) and HTMX
      sign button where pdf exists and status is PENDIENTE. Template:
      templates/legalization/detail.html. Test: test_detail_document_status_badges.
- [x] 4.3 Create sign action view
      **→ satisfied by CHG-301: SignDocumentHTMXView (views.py) + sign_form.html
      partial.** HTMX GET shows confirmation form; POST calls sign_legal_document
      and re-renders document_row.html on success.
- [x] 4.4 Add URLs for legalization views
      **→ satisfied by CHG-301: urls.py** — list, detail, sign_document routes
      wired under app_name="legalization".
- [x] 4.5 Add to base.html menu (R-JUNTA role)
      **→ Batch B** — Legalización nav-link added to R-JUNTA section of navbar,
      following {% for ur in user_roles %}{% if ur.role.code == 'R-JUNTA' %} pattern,
      links to {% url 'legalization:list' %}.


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
- [x] 7.2 Add list filters by status and beneficiary
      **→ Batch B** — LegalizationProcessAdmin.list_filter added "beneficiary";
      LegalDocumentAdmin already had status filter (CHG-301).


---

## Batch Notes — CHG-302 Batch B (this implementation)

**Completed in this batch:**
- test_views.py: 9 request-level tests covering list (R-JUNTA all, beneficiary own,
  unauthenticated redirect) and detail (R-JUNTA any, beneficiary own, other 404,
  document context + status badges)
- LegalizationListView + LegalizationDetailView (already in views.py from CHG-301)
  verified working with proper role gating; list.html and detail.html templates exist
  (created by previous worker on this branch)
- SignDocumentHTMXView + URLs confirmed functional — satisfies 4.3/4.4
- LegalizationProcessAdmin.list_filter added "beneficiary" filter (7.2)
- base.html: Legalización menu link for R-JUNTA role (4.5)
- 80 total tests green (71 pre-existing + 9 new)

**Batch C still owns:**
- Nothing for CHG-302. All tasks complete.

**Deferrals:**
- None.
