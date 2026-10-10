# Tasks: Asignación de Roles a Usuarios

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 350-450 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Suggested split | PR 1: Models/Sync → PR 2: Assignment/Views/Tests |
| Delivery strategy | ask-on-risk |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Core model sync infrastructure | PR 1 | Foundation for all role/permission operations |
| 2 | User-facing role management | PR 2 | Depends on PR 1, includes views/templates/tests |

## Phase 1: Model & Sync Infrastructure

- [x] 1.1 Add `group` ForeignKey to `Role` model in `apps/accounts/models.py`
- [x] 1.2 Add `auth_permission` ForeignKey to `Permission` model in `apps/accounts/models.py`
- [x] 1.3 Create `sync_role_to_group()` service in `apps/accounts/services/sync.py`
- [x] 1.4 Create `sync_permission_to_auth_perm()` service in `apps/accounts/services/sync.py`
- [x] 1.5 Implement `full_sync_roles_permissions` management command in `apps/accounts/management/commands/sync_roles.py`

## Phase 2: Role Assignment Services

- [x] 2.1 Implement `assign_role_to_user()` in `apps/accounts/services/assignment.py`
- [x] 2.2 Implement `revoke_role_from_user()` in `apps/accounts/services/assignment.py`
- [x] 2.3 Build `get_user_effective_permissions()` with caching in `apps/accounts/services/permissions.py`

## Phase 3: Views & Integration

- [x] 3.1 Create `UserRoleListView` in `apps/accounts/views/roles.py`
- [x] 3.2 Create `UserRoleAssignView` with POST handler in `apps/accounts/views/roles.py`
- [x] 3.3 Create `UserRoleRevokeView` in `apps/accounts/views/roles.py`
- [x] 3.4 Implement `UserRoleHistoryView` with audit log integration
- [x] 3.5 Add URL patterns to `apps/accounts/urls.py`
- [x] 3.6 Update user detail template in `templates/accounts/user_detail.html`
- [x] 3.7 Create role assignment form in `templates/accounts/role_assignment_form.html`

## Phase 4: Verification

- [x] 4.1 Write unit tests for `sync_role_to_group()` covering group creation
- [x] 4.2 Test `assign_role_to_user()` with permission inheritance
- [x] 4.3 Verify `get_user_effective_permissions()` handles role revocation
- [x] 4.4 Validate UI templates render role data correctly

## Phase 5: Cleanup

- [x] 5.1 Update API documentation in `docs/api/roles.md`
- [x] 5.2 Add migration notes to `CHANGES.md`
