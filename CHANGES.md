# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added

#### CHG-112: Asignación de Roles a Usuarios

**Description**: Implemented role assignment functionality with Django auth integration.

**Changes:**

- **Models** (`apps/accounts/models.py`):
  - Added `group` OneToOneField to Role model (links to auth.Group)
  - Added `auth_permission` OneToOneField to Permission model (links to auth.Permission)

- **Services** (`apps/accounts/services/`):
  - Created `sync.py` with `sync_role_to_group()` and `sync_permission_to_auth_perm()`
  - Created `assignment.py` with `assign_role_to_user()` and `revoke_role_from_user()`
  - Created `permissions.py` with `get_user_effective_permissions()` and cache functions

- **Management Commands** (`apps/accounts/management/commands/`):
  - Created `sync_roles.py` to sync roles/permissions with Django auth

- **Views** (`apps/accounts/views/admin_views.py`):
  - Updated UserRoleAssignView to use assign_role_to_user() service
  - Updated UserRoleRevokeView to use revoke_role_from_user() service
  - Added UserRoleHistoryView for role change history

- **URLs** (`apps/accounts/admin_urls.py`):
  - Created new URL patterns for user role management

- **Templates** (`templates/accounts/admin/`):
  - Created admin_base.html
  - Created users/detail.html
  - Created users/roles.html
  - Created users/role_history.html

**Migrations:**
- `0004_role_group.py` - Adds group field to Role
- `0005_permission_auth_permission.py` - Adds auth_permission field to Permission

**Breaking Changes:**
- None

**Deprecations:**
- None

**Known Issues:**
- None

---

## [2026-07-02]

### Previous Changes

See git history for details.
