"""Role assignment services."""
import uuid
from django.db import transaction
from apps.accounts.models import CustomUser, Role, UserRole
from apps.audit.services import log_audit_event
from .permissions import invalidate_user_permissions_cache


def assign_role_to_user(
    user: CustomUser, 
    role: Role, 
    convocation_scope: str = None,
    actor: CustomUser = None
) -> UserRole:
    """
    Assign a role to a user.
    
    Args:
        user: The user to assign the role to
        role: The role to assign
        convocation_scope: Optional convocation scope ID
        actor: The user performing the assignment (for audit). Defaults to the user being assigned.
        
    Returns:
        The created UserRole instance
        
    Raises:
        ValueError: If the role doesn't have a Django group
    """
    # Check if role has a group
    if role.group is None:
        raise ValueError(f"Role {role.code} doesn't have a Django group. Sync it first.")
    
    with transaction.atomic():
        # Create UserRole instance
        user_role = UserRole.objects.create(
            user=user,
            role=role,
            convocation_scope_id=convocation_scope
        )
        
        # Add user to the role's Django group (this gives them the permissions)
        user.groups.add(role.group)
        
        # Log to audit
        # Generate deterministic UUID for audit since UserRole uses integer PK
        audit_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"accounts.UserRole.{user_role.id}")
        log_audit_event(
            actor=actor or user,
            action="ASSIGN_ROLE",
            entity="UserRole",
            entity_id=audit_uuid,
            changes={
                "before": None,
                "after": {
                    "user_id": str(user.id),
                    "role_id": str(role.id),
                    "convocation_scope": convocation_scope
                }
            }
        )
        
        # Invalidate permissions cache since user's groups have changed
        invalidate_user_permissions_cache(user)
        
        return user_role


def revoke_role_from_user(user_role: UserRole, actor: CustomUser = None):
    """
    Revoke a role from a user.
    
    Args:
        user_role: The UserRole instance to revoke
        actor: The user performing the revocation (for audit). Defaults to the user whose role is being revoked.
    """
    with transaction.atomic():
        # Get the user and role before deletion
        user = user_role.user
        role = user_role.role
        
        # Generate audit UUID before deleting
        audit_uuid = uuid.uuid5(uuid.NAMESPACE_OID, f"accounts.UserRole.{user_role.id}")
        
        # Remove user from the role's Django group
        if role.group:
            user.groups.remove(role.group)
        
        # Delete UserRole instance
        user_role.delete()
        
        # Log to audit
        log_audit_event(
            actor=actor or user,
            action="REVOKE_ROLE",
            entity="UserRole",
            entity_id=audit_uuid,
            changes={
                "before": {
                    "user_id": str(user.id),
                    "role_id": str(role.id),
                    "convocation_scope": user_role.convocation_scope_id
                },
                "after": None
            }
        )
        
        # Invalidate permissions cache since user's groups have changed
        invalidate_user_permissions_cache(user)