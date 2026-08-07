"""Signals for admin actions audit logging."""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from apps.audit.services import log_audit_event
from apps.accounts.models import Role, UserRole

User = get_user_model()


def get_current_user():
    """Get the current user from thread local storage or request."""
    # This would be implemented to get the user from the request context
    # For now, returns None - actual implementation would use middleware
    return None


@receiver(post_save, sender=User)
def log_user_change(sender, instance, created, **kwargs):
    """Log user creation and updates."""
    action = 'CREATE' if created else 'UPDATE'
    
    try:
        log_audit_event(
            actor=get_current_user(),
            action=action,
            entity='CustomUser',
            entity_id=instance.id,
            changes={
                'email': instance.email,
                'documento': instance.documento,
                'is_active': instance.is_active,
            },
            module='accounts',
        )
    except Exception:
        # Don't let audit failures break user operations
        pass


@receiver(post_save, sender=Role)
def log_role_change(sender, instance, created, **kwargs):
    """Log role creation and updates."""
    action = 'CREATE' if created else 'UPDATE'
    
    try:
        log_audit_event(
            actor=get_current_user(),
            action=action,
            entity='Role',
            entity_id=instance.id,
            changes={
                'code': instance.code,
                'name': instance.name,
                'type': instance.type,
            },
            module='accounts',
        )
    except Exception:
        pass


@receiver(post_save, sender=UserRole)
def log_user_role_change(sender, instance, created, **kwargs):
    """Log user role assignments."""
    action = 'CREATE' if created else 'UPDATE'
    
    try:
        log_audit_event(
            actor=get_current_user(),
            action=action,
            entity='UserRole',
            entity_id=instance.id,
            changes={
                'user_id': instance.user_id,
                'role_id': instance.role_id,
                'convocation_scope_id': instance.convocation_scope_id,
            },
            module='accounts',
        )
    except Exception:
        pass


@receiver(post_delete, sender=UserRole)
def log_user_role_delete(sender, instance, **kwargs):
    """Log user role revocations."""
    try:
        log_audit_event(
            actor=get_current_user(),
            action='DELETE',
            entity='UserRole',
            entity_id=instance.id,
            changes={
                'user_id': instance.user_id,
                'role_id': instance.role_id,
                'convocation_scope_id': instance.convocation_scope_id,
            },
            module='accounts',
        )
    except Exception:
        pass