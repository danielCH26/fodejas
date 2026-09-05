# Tasks — CHG-303 Disbursement

## 1. Setup

- [ ] 1.1 Create app `apps/treasury/` if not exists
- [ ] 1.2 Add to INSTALLED_APPS
- [ ] 1.3 Create initial migration

## 2. Models

- [ ] 2.1 Create `DisbursementAuthorization` model
- [ ] 2.2 Add status choices
- [ ] 2.3 Add foreign keys to legalization
- [ ] 2.4 Generate migration

## 3. Services

- [ ] 3.1 Create `TreasuryService` class
- [ ] 3.2 Implement `create_authorization()`
- [ ] 3.3 Implement `authorize()` method
- [ ] 3.4 Implement `send_to_treasury()`
- [ ] 3.5 Implement `confirm_payment()`

## 4. Views

- [ ] 4.1 Create authorization list view
- [ ] 4.2 Create authorization detail view
- [ ] 4.3 Create authorize action view
- [ ] 4.4 Create treasury reconciliation view
- [ ] 4.5 Add URLs

## 5. Integration

- [ ] 5.1 Check legalization is complete before authorizing
- [ ] 5.2 Add audit logging

## 6. Tests

- [ ] 6.1 Test authorization workflow
- [ ] 6.2 Test treasury confirmation

## 7. Admin

- [ ] 7.1 Register models in admin
