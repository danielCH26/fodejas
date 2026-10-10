# Tasks — CHG-303 Disbursement

## 1. Setup

- [x] 1.1 Create app `apps/treasury/` if not exists
  *(pre-existing from CHG-802: commit f849a64 — celery infrastructure + sweeps)*
- [x] 1.2 Add to INSTALLED_APPS
  *(pre-existing from CHG-802: config/settings.py line 141)*
- [x] 1.3 Create initial migration
  *(pre-existing from CHG-802: apps/treasury/migrations/0001_initial.py)*

## 2. Models

- [x] 2.1 Create `DisbursementAuthorization` model
  *(pre-existing from CHG-802: apps/treasury/models.py)*
- [x] 2.2 Add status choices
  *(pre-existing: PENDIENTE, AUTORIZADO, ORDENADO, RECIBIDO, PAGADO, RECHAZADO, VENCIDO)*
- [x] 2.3 Add foreign keys to legalization
  *(pre-existing: legalization_process FK)*
- [x] 2.4 Generate migration
  *(pre-existing from CHG-802: migrations 0001, 0002)*

## 3. Services

- [x] 3.1 Create `TreasuryService` class
  *(pre-existing from CHG-802: apps/treasury/services.py)*
- [x] 3.2 Implement `create_authorization()` (guard 5.1 + amount > 0)
  *(gap-fill: guard was pre-existing; amount > 0 added in Batch A)*
- [x] 3.3 Implement `authorize()` method (doble firma)
  *(gap-fill: self-signing prevention added in Batch A)*
- [x] 3.4 Implement `send_to_treasury()` (adjuntos normativos)
  *(gap-fill: 4-doc validation + attachment manifest added in Batch A)*
- [x] 3.5 Implement `confirm_payment()`
  *(pre-existing from CHG-802)*

## 4. Views

- [x] 4.1 Create authorization list view *(Batch B)*
  *(`DisbursementAuthorizationListView` — role-gated: R-JUNTA+R-COORDINADOR;
    shows PENDIENTE+AUTORIZADO rows; VENCIDO highlighted in badge;
    list template: `treasury/disbursement_list.html`)*
- [x] 4.2 Create authorization detail view *(Batch B)*
  *(`DisbursementAuthorizationDetailView` — authorization with legalization
    process ref, dual-signature state, 4 required attachment types,
    treasury order info, payment proof; detail template:
    `treasury/disbursement_detail.html`)*
- [x] 4.3 Create authorize action view *(Batch B — HTMX)*
  *(`AuthorizeDisbursementHTMXView` — GET shows confirm form, POST calls
    `TreasuryService.authorize(user, role)`; surfaces self-signing and
    duplicate-role errors inline; partials: `authorize_form.html`,
    `signature_status.html`, `authorize_error.html`)*
- [x] 4.4 Create treasury reconciliation view
  *(pre-existing: apps/treasury/views.py — TreasuryReconciliationView)*
- [x] 4.5 Add URLs *(Batch B)*
  *(`disbursement_list`, `disbursement_detail`, `authorize` routes under
    app_name="treasury"; list at `/treasury/`)*
- [x] 4.6 Menu entry *(Batch B)*
  *(`templates/base.html` — R-JUNTA block: link to
    `treasury:disbursement_list` with `<i class="bi bi-wallet2"></i>` icon)*
- [x] 4.7 View tests *(Batch B)*
  *(`test_views_disbursement.py`: 18 tests — list gating (R-JUNTA 200,
    R-COORDINADOR 200, other 403, staff 200), detail context (process,
    dual-signature state, attachments), authorize POST happy path,
    self-sign rejection, duplicate-role rejection, URL routing)*

## 5. Integration

- [x] 5.1 Check legalization is complete before authorizing
  *(pre-existing: create_authorization() already checked status==LEGALIZADO)*
- [x] 5.2 Add audit logging
  *(gap-fill: all service methods now emit AUDIT_DISBURSEMENT_* events)*

## 6. Tests

- [x] 6.1 Test authorization workflow
  *(test_service_audit.py: TestDobleFirmaHappyPath)*
- [x] 6.2 Test treasury confirmation
  *(test_service_audit.py: TestConfirmPayment, TestSendToTreasuryAttachments)*
- [x] 6.3 Test double-firma violations (self-signing, duplicate role)
  *(test_service_audit.py: TestDobleFirmaSelfSigning)*
- [x] 6.4 Test legalization guard
  *(test_service_audit.py: TestCreateAuthorizationGuard)*
- [x] 6.5 Test adjuntos normativos (with/without all 4 docs)
  *(test_service_audit.py: TestSendToTreasuryAttachments)*
- [x] 6.6 Test confirm_payment with/without proof (D2: comprobante validation)
  *(test_service_audit.py: TestConfirmPayment)*
- [x] 6.7 Test reject + terminal state guard
  *(test_service_audit.py: TestReject)*
- [x] 6.8 Test VENCIDO sweep integration
  *(test_service_audit.py: TestVencidoSweepIntegration)*
- [x] 6.9 Test reconciliation permission checks
  *(test_service_audit.py: TestReconciliationPermission)*
- [x] 6.10 Test monetary field (amount > 0, immutability)
  *(test_service_audit.py: TestMonetaryField)*

## 7. Admin

- [x] 7.1 Register models in admin
  *(apps/treasury/admin.py: DisbursementAuthorizationAdmin — list_display,
  list_filter by status, search by order/beneficiary)*

---

## Batch Notes

**Batch A scope** (this change — domain/service/admin/tests):
- Domain gaps filled: doble firma self-signing prevention, 4-doc attachment
  validation in `send_to_treasury()`, audit events in all service methods,
  amount > 0 validation.
- Admin: `DisbursementAuthorizationAdmin` with status list_filter,
  list_display (dates, status, amount), search.
- Full test suite: 46 treasury service/admin tests, all passing.
- Batch B adds 18 view tests (all passing); treasury total: 65 tests.

**Batch B scope** (views + templates — DONE):
- 4.1: `DisbursementAuthorizationListView` — role-gated (R-JUNTA+R-COORDINADOR);
  list of PENDIENTE+AUTORIZADO rows; `treasury/disbursement_list.html`
- 4.2: `DisbursementAuthorizationDetailView` — authorization+process context,
  dual-signature state, 4 required attachments, treasury order info,
  payment proof; `treasury/disbursement_detail.html`
- 4.3: `AuthorizeDisbursementHTMXView` — GET confirm form / POST signs;
  HTMX partials: `authorize_form.html`, `signature_status.html`,
  `authorize_error.html`
- 4.5: URLs — list `/treasury/`, detail `/treasury/<uuid>/`,
  authorize `/treasury/<uuid>/autorizar/`
- 4.6: Menu entry — R-JUNTA block in `templates/base.html`
- 4.7: 18 view tests — all passing

**Batch B known simplifications**:
- ACTO_ADMINISTRATIVO attachment in detail template links to a note saying
  "acto admin pendiente de integrar con Gobernanza" — no governance acto
  linking (outside CHG-303 scope per AGENTS.md §7).
- Comprobante attachment in confirm-payment form enforced at reconciliation
  view level (pre-existing); not re-implemented here.

**Remaining for CHG-303**: nothing — all Batch B tasks complete.

**Assumption re: 4th normative attachment**:
The design.md D1 does not enumerate the 4 attachment types explicitly.
Using the 4 documents already defined in the domain:
  1. PAGARE
  2. CARTA_INSTRUCCIONES
  3. CONTRATO
  4. ACTO_ADMINISTRATIVO (new: administrative act / resolución de otorgamiento)
If Batch B or the design enumerates a different 4th type, update
`REQUIRED_ATTACHMENT_TYPES` in `TreasuryService` and `treasury_order_attachments`
accordingly.

**gitignore note**:
`apps/treasury/` is on the `.gitignore` "treasury/" pattern (parent: root
`treasury/` for local test artifacts). Use `git add -f` to force-add.
