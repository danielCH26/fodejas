"""Sync services for role and permission integration with Django auth system."""
from django.contrib.auth.models import Group, Permission as AuthPermission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from apps.accounts.models import Role, Permission


def sync_role_to_group(role: Role) -> Group:
    """
    Sync a Role to a Django auth.Group.
    
    Args:
        role: The Role instance to sync
        
    Returns:
        The Group instance (created or existing)
    
    Behavior:
        - If role already has a group, return it
        - If no group exists, create one using role.code as name
        - If a group with that name already exists, use it
        - Link the group to role.group
    """
    # If role already has a group, return it
    if role.group is not None:
        return role.group
    
    # Get or create group with role.code as name
    group, created = Group.objects.get_or_create(name=role.code)
    
    # Link group to role
    role.group = group
    role.save(update_fields=["group"])
    
    return group


def sync_permission_to_auth_perm(permission: Permission) -> AuthPermission:
    """
    Sync a custom Permission to a Django auth.Permission.
    
    Args:
        permission: The Permission instance to sync
        
    Returns:
        The auth.Permission instance (created or existing)
    
    Behavior:
        - If permission already has auth_permission, return it
        - Get or create ContentType for the app_label
        - Get or create auth.Permission with codename = permission.action
        - Link auth_permission to permission.auth_permission
        
    Note: Django auth.Permission doesn't store scope/stage, so we only
          sync the app_label and action.
    """
    # If permission already has auth_permission, return it
    if permission.auth_permission is not None:
        return permission.auth_permission
    
    # Get or create ContentType for the app_label
    # In Django, content_type is associated with a model, not an app.
    # We need to find a model in the app, or create a placeholder.
    # For simplicity, we'll use the Permission model itself.
    content_type, _ = ContentType.objects.get_or_create(
        app_label=permission.app_label,
        model="permission"  # Using lowercase model name
    )
    
    # Create a name for the permission
    # Format: "Can {action} in {app_label}"
    name = f"Can {permission.action} in {permission.app_label}"
    
    # Get or create auth.Permission
    auth_perm, created = AuthPermission.objects.get_or_create(
        content_type=content_type,
        codename=permission.action,
        defaults={"name": name}
    )
    
    # Link auth_permission to permission
    permission.auth_permission = auth_perm
    permission.save(update_fields=["auth_permission"])
    
    return auth_perm