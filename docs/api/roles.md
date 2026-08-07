# Roles API Documentation

## Overview

This document describes the role management functionality implemented in CHG-112.

## Services

### Sync Services

#### `sync_role_to_group(role: Role) -> Group`

Synchronizes a domain Role to a Django auth.Group.

**Parameters:**
- `role` (Role): The domain Role instance

**Returns:**
- `Group`: The Django auth.Group instance (created or existing)

**Behavior:**
- If role already has a group, returns it
- If no group exists, creates one using role.code as name
- Links group to role.group

#### `sync_permission_to_auth_perm(permission: Permission) -> AuthPermission`

Synchronizes a domain Permission to a Django auth.Permission.

**Parameters:**
- `permission` (Permission): The domain Permission instance

**Returns:**
- `AuthPermission`: The Django auth.Permission instance

### Assignment Services

#### `assign_role_to_user(user, role, convocation_scope=None, actor=None) -> UserRole`

Assigns a role to a user with Django group integration.

**Parameters:**
- `user` (CustomUser): The user to assign the role to
- `role` (Role): The role to assign
- `convocation_scope` (str, optional): Convocation ID for scope-specific access
- `actor` (CustomUser, optional): User performing the assignment (for audit)

**Returns:**
- `UserRole`: The created UserRole instance

**Behavior:**
- Creates UserRole instance
- Adds user to role's Django group (granting permissions)
- Logs to audit
- Invalidates permissions cache

**Raises:**
- `ValueError`: If role doesn't have a Django group

#### `revoke_role_from_user(user_role, actor=None)`

Revokes a role from a user.

**Parameters:**
- `user_role` (UserRole): The UserRole instance to revoke
- `actor` (CustomUser, optional): User performing the revocation (for audit)

**Behavior:**
- Removes user from role's Django group
- Deletes UserRole instance
- Logs to audit
- Invalidates permissions cache

### Permissions Services

#### `get_user_effective_permissions(user) -> set`

Gets all effective permissions for a user with caching.

**Parameters:**
- `user` (CustomUser): The user to get permissions for

**Returns:**
- `set`: Set of permission strings in format "app_label.codename"

**Behavior:**
- Returns union of direct user permissions and group permissions
- Results are cached for 5 minutes

#### `invalidate_user_permissions_cache(user)`

Invalidates the permissions cache for a user.

**Parameters:**
- `user` (CustomUser): The user whose cache to invalidate

## Management Commands

### `python manage.py sync_roles`

Synchronizes all roles and permissions with Django auth system.

**Options:**
- `--dry-run`: Show what would be synced without making changes

**Usage:**
```bash
# Dry run to see what would be synced
python manage.py sync_roles --dry-run

# Actually perform the sync
python manage.py sync_roles
```

## Integration with Django Permissions

The implementation integrates with Django's native permission system:

1. **Role → Group**: Each Role syncs to a Django Group
2. **Permission → AuthPermission**: Each Permission syncs to Django auth.Permission
3. **UserRole → User.groups**: Assigning a role adds user to the Group

This allows using Django's native permission checks:

```python
# Check if user has permission
if user.has_perm('applications.view_convocatory'):
    # User has the permission via their role

# Get all permissions
permissions = user.get_all_permissions()
```

## URL Patterns

| URL | View | Description |
|-----|------|-------------|
| `/accounts/admin/users/` | UserListView | List all users |
| `/accounts/admin/users/<pk>/` | UserDetailView | User details with roles |
| `/accounts/admin/users/<pk>/roles/` | UserRoleAssignView | Assign roles to user |
| `/accounts/admin/users/<pk>/roles/<role_id>/revoke/` | UserRoleRevokeView | Revoke role |
| `/accounts/admin/users/<pk>/roles/history/` | UserRoleHistoryView | Role change history |

## Audit Events

Role assignments and revocations are logged with the following actions:

- `ASSIGN_ROLE` - When a role is assigned to a user
- `REVOKE_ROLE` - When a role is revoked from a user
