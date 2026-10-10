"""Selectors for audit app."""

from django.db.models import Q
from django.db.models.query import QuerySet

from .models import AuditEvent
from .services import verify_chain


def get_audit_events(
    actor=None,
    action=None,
    entity=None,
    entity_id=None,
    module=None,
    timestamp_from=None,
    timestamp_to=None,
    search=None,
) -> QuerySet:
    """
    Get filtered audit events queryset.

    Args:
        actor: Filter by actor user ID
        action: Filter by action (CREATE, UPDATE, DELETE, etc.)
        entity: Filter by entity name
        entity_id: Filter by entity UUID
        module: Filter by module name
        timestamp_from: Filter events from this datetime
        timestamp_to: Filter events until this datetime
        search: General search in entity or module

    Returns:
        QuerySet of AuditEvent ordered by timestamp descending
    """
    queryset = AuditEvent.objects.select_related("actor").all()

    if actor:
        queryset = queryset.filter(actor_id=actor)

    if action:
        queryset = queryset.filter(action=action)

    if entity:
        queryset = queryset.filter(entity=entity)

    if entity_id:
        queryset = queryset.filter(entity_id=entity_id)

    if module:
        queryset = queryset.filter(module=module)

    if timestamp_from:
        queryset = queryset.filter(timestamp__gte=timestamp_from)

    if timestamp_to:
        queryset = queryset.filter(timestamp__lte=timestamp_to)

    if search:
        queryset = queryset.filter(Q(entity__icontains=search) | Q(module__icontains=search))

    return queryset.order_by("-timestamp")


def get_audit_event_by_id(event_id: str) -> AuditEvent | None:
    """
    Get a single audit event by ID.

    Args:
        event_id: UUID of the audit event

    Returns:
        AuditEvent instance or None if not found
    """
    try:
        return AuditEvent.objects.select_related("actor").get(id=event_id)
    except AuditEvent.DoesNotExist:
        return None


def get_audit_entities() -> list[str]:
    """Get list of distinct entity names in audit log."""
    return list(AuditEvent.objects.values_list("entity", flat=True).distinct().order_by())


def get_audit_actions() -> list[str]:
    """Get list of distinct action types in audit log."""
    return list(AuditEvent.objects.values_list("action", flat=True).distinct().order_by())


def get_audit_modules() -> list[str]:
    """Get list of distinct modules in audit log."""
    return list(AuditEvent.objects.values_list("module", flat=True).distinct().order_by())


def get_audit_stats() -> dict:
    """
    Get basic statistics about audit events.

    Returns:
        Dict with counts by action, entity, and total
    """
    from django.db.models import Count

    total = AuditEvent.objects.count()

    by_action = dict(
        AuditEvent.objects.values("action")
        .annotate(count=Count("id"))
        .values_list("action", "count")
    )

    by_entity = dict(
        AuditEvent.objects.values("entity")
        .annotate(count=Count("id"))
        .values_list("entity", "count")
    )

    return {
        "total": total,
        "by_action": by_action,
        "by_entity": by_entity,
    }


def verify_audit_chain() -> dict:
    """
    Verify the integrity of the audit chain.

    Returns:
        Dict with is_valid, last_valid_hash, break_point
    """
    return verify_chain()
