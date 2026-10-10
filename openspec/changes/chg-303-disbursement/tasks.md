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

- [ ] 4.1 Create authorization list view *(Batch B)*
- [ ] 4.2 Create authorization detail view *(Batch B)*
- [ ] 4.3 Create authorize action view *(Batch B)*
- [ ] 4.4 Create treasury reconciliation view
  *(pre-existing: apps/treasury/views.py — TreasuryReconciliationView)*
- [x] 4.5 Add URLs
  *(pre-existing: reconciliation URL only; list/detail/authorize URLs are Batch B)*

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
- Full test suite: 46 treasury tests, all passing.

**Batch B scope** (views + templates — deferred):
- 4.1: Authorization list view (GET)
- 4.2: Authorization detail view (GET)
- 4.3: Authorize action view (POST — triggers doble firma flow)
- 4.5: URL patterns for list/detail/authorize (menu entry)
- Views must enforce comprobante attachment in the confirm-payment form
  (design.md D2: "Validación en UI" for falta comprobante)

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
