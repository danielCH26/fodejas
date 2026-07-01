"""Audit service for logging events."""
import hashlib
import uuid
from django.db import transaction
from django.utils import timezone

from .models import AuditEvent


def calculate_hash(timestamp, actor_id, action, entity, entity_id, changes, previous_hash):
    """
    Calculate SHA-256 hash for an audit record.

    Args:
        timestamp: datetime object
        actor_id: user ID or None
        action: CREATE, UPDATE, DELETE, etc.
        entity: model name
        entity_id: UUID of the entity
        changes: JSON dict with before/after
        previous_hash: hash of previous record

    Returns:
        SHA-256 hex digest
    """
    data = f"{timestamp}|{actor_id}|{action}|{entity}|{entity_id}|{changes}|{previous_hash}"
    return hashlib.sha256(data.encode()).hexdigest()


@transaction.atomic
def log_audit_event(
    actor,
    action,
    entity,
    entity_id,
    changes=None,
    ip_address=None,
    user_agent=None,
    module=None,
):
    """
    Log an audit event with hash chain integrity.

    Args:
        actor: User instance or None for system actions
        action: CREATE, UPDATE, DELETE, LOGIN, LOGOUT, ACCESS
        entity: Model name (e.g., "Convocatoria", "User")
        entity_id: UUID of the affected entity
        changes: Dict with 'before' and 'after' keys for UPDATE
        ip_address: Client IP address
        user_agent: Client user agent string
        module: App label (e.g., "accounts", "convocatories")

    Returns:
        AuditEvent instance
    """
    # Get previous hash
    previous_hash = AuditEvent.get_previous_hash()

    # Create timestamp
    timestamp = timezone.now()

    # Calculate hash
    current_hash = calculate_hash(
        timestamp=timestamp,
        actor_id=actor.id if actor else None,
        action=action,
        entity=entity,
        entity_id=str(entity_id),
        changes=changes,
        previous_hash=previous_hash,
    )

    # Create event
    event = AuditEvent.objects.create(
        timestamp=timestamp,
        actor=actor,
        action=action,
        entity=entity,
        entity_id=entity_id if isinstance(entity_id, uuid.UUID) else uuid.UUID(str(entity_id)),
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent or "",
        module=module or "unknown",
        previous_hash=previous_hash,
        current_hash=current_hash,
        is_valid=True,
    )

    return event


def verify_chain():
    """
    Verify the integrity of the audit chain.

    Returns:
        dict with 'is_valid', 'last_valid_hash', 'break_point'
    """
    events = AuditEvent.objects.order_by("timestamp")

    if not events.exists():
        return {
            "is_valid": True,
            "last_valid_hash": "0" * 64,
            "break_point": None,
        }

    expected_previous = "0" * 64

    for event in events:
        # Check if previous hash matches
        if event.previous_hash != expected_previous:
            return {
                "is_valid": False,
                "last_valid_hash": expected_previous,
                "break_point": event.id,
            }

        # Verify current hash
        calculated_hash = calculate_hash(
            timestamp=event.timestamp,
            actor_id=event.actor_id,
            action=event.action,
            entity=event.entity,
            entity_id=str(event.entity_id),
            changes=event.changes,
            previous_hash=event.previous_hash,
        )

        if event.current_hash != calculated_hash:
            return {
                "is_valid": False,
                "last_valid_hash": expected_previous,
                "break_point": event.id,
            }

        # Move to next
        expected_previous = event.current_hash

    return {
        "is_valid": True,
        "last_valid_hash": expected_previous,
        "break_point": None,
    }
