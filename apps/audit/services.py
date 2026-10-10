"""Audit service for logging events (CAP-022 hash chain)."""
import hashlib
import json
import logging
import uuid

from django.db import transaction

from .models import AuditEvent

logger = logging.getLogger(__name__)


# Namespace used to coerce non-UUID primary keys (e.g. ``BigAutoField``
# on the catalog models) into a deterministic UUID. The namespace is
# fixed so the same ``(entity, instance_id)`` always maps to the same
# UUID, regardless of which worker or test process writes the row.
_NON_UUID_ENTITY_NAMESPACE = uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


def coerce_entity_id(entity_id) -> uuid.UUID:
    """Return a deterministic UUID for any ``entity_id`` value.

    The ``AuditEvent`` schema declares ``entity_id`` as a ``UUIDField``.
    Most audited domain models already use ``UUIDField`` primary keys,
    but the catalog models in ``apps.core`` use ``BigAutoField``. We
    coerce non-UUID values to UUID5 using a fixed namespace so the
    value is still globally unique within the audit chain.

    Args:
        entity_id: ``uuid.UUID``, ``str`` (UUID or integer), or
            ``int`` (catalog model PK).

    Returns:
        ``uuid.UUID`` suitable for ``AuditEvent.entity_id``.
    """
    if isinstance(entity_id, uuid.UUID):
        return entity_id
    if isinstance(entity_id, str):
        try:
            return uuid.UUID(entity_id)
        except (ValueError, AttributeError):
            pass
    return uuid.uuid5(_NON_UUID_ENTITY_NAMESPACE, str(entity_id))


class AuditChainLockError(RuntimeError):
    """Raised when the audit chain head lock cannot be acquired."""


def calculate_hash(timestamp, actor_id, action, entity, entity_id, changes, previous_hash):
    """
    Calculate SHA-256 hash for an audit record.
    """
    if changes is None:
        changes_str = "null"
    else:
        changes_str = json.dumps(changes, sort_keys=True, default=str)

    data = (
        f"{timestamp}|{actor_id}|{action}|{entity}|"
        f"{entity_id}|{changes_str}|{previous_hash}"
    )
    return hashlib.sha256(data.encode()).hexdigest()


def _lock_chain_head():
    """Acquire SELECT ... FOR UPDATE on the latest audit event.

    Returns the current_hash of the chain head, or the initial
    ``"0" * 64`` if the chain is empty. Must be called inside an
    active transaction. Without the lock, two concurrent writers
    can both read the same ``previous_hash`` and produce a fork in
    the chain (AUD-003).

    Returns:
        str: hex SHA-256 of the previous record (or zeros for empty).
    """
    head = (
        AuditEvent.objects.select_for_update()
        .order_by("-timestamp")
        .first()
    )
    if head is None:
        return "0" * 64
    return head.current_hash


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
    Log an audit event with hash chain integrity (CAP-022).

    The function takes a ``SELECT ... FOR UPDATE`` lock on the
    current chain head so that concurrent writers serialize and the
    hash chain cannot fork (CHG-801 / AUD-003).

    When ``actor`` is ``None`` (signal fired outside an
    authenticated request, management command, background task),
    the event is recorded with ``actor=None`` and the metadata
    sentinel ``actor_is_system=True`` so downstream verifiers can
    distinguish system actions from user actions (CHG-801 /
    AUD-002).

    **Important — timestamp handling**: Django's ``auto_now_add=True``
    on ``AuditEvent.timestamp`` overrides any value passed to
    ``objects.create(timestamp=...)`` because ``Field.pre_save``
    unconditionally re-stamps the field on INSERT. As a result we
    cannot compute the hash from our own ``timezone.now()`` value
    and expect the stored row to match — they would differ by the
    microseconds elapsed between hash compute and INSERT. Instead
    we let ``AuditEvent.save()`` (which runs in the same atomic
    block and sees the post-``pre_save`` timestamp) compute
    ``current_hash`` from the canonical fields. The hash function
    in ``apps.audit.models.calculate_hash`` mirrors this service
    helper so the chain validates.

    Args:
        actor: ``CustomUser`` instance or ``None`` for system actions.
        action: CREATE, UPDATE, DELETE, LOGIN, LOGOUT, ACCESS,
            ELECTRONIC_SIGNATURE, or any short event code (<= 20 chars).
        entity: Model name (e.g. "Convocatory", "Estrato").
        entity_id: UUID of the affected entity.
        changes: Dict with ``before``/``after`` keys for UPDATE
            (or arbitrary metadata for CREATE / DELETE).
        ip_address: Client IP address.
        user_agent: Client user agent string.
        module: App label (e.g. "accounts", "convocatories").

    Returns:
        ``AuditEvent`` instance.

    Raises:
        AuditChainLockError: if the chain head lock cannot be acquired.
    """
    # 1) Lock the chain head and read the previous hash. The lock
    #    holds for the rest of this transaction; any concurrent
    #    writer will block until we commit or roll back.
    try:
        previous_hash = _lock_chain_head()
    except Exception as exc:
        # Surface as a domain-level exception so callers (signals,
        # domain services) can decide whether to fail loud or log
        # and continue. We do NOT swallow this in the helper.
        logger.exception("audit: failed to lock chain head")
        raise AuditChainLockError(str(exc)) from exc

    # 2) Normalize payload. If actor is None we annotate metadata so
    #    the chain records the system-origin sentinel.
    if actor is None and isinstance(changes, dict):
        changes = {**changes, "actor_is_system": True}

    # 3) Coerce entity_id to a UUID so the model accepts it.
    entity_uuid = coerce_entity_id(entity_id)

    # 4) Persist. Django's ``auto_now_add=True`` stamps the timestamp
    #    during INSERT, so we cannot compute the hash from a
    #    ``timezone.now()`` we capture here (the stored value would
    #    differ by a few microseconds). Instead:
    #
    #    a) Insert WITHOUT ``current_hash`` (and without an explicit
    #       timestamp — let ``auto_now_add`` stamp it).
    #    b) Read the persisted event back so ``event.timestamp`` is
    #       the canonical stamped value.
    #    c) Compute ``current_hash`` from the persisted fields.
    #    d) ``save(update_fields=["current_hash"])`` so the row is
    #       updated without firing ``post_save`` again.
    #
    #    Both helpers (``services.calculate_hash`` and
    #    ``AuditEvent.calculate_hash``) canonicalize ``changes`` the
    #    same way so the chain validates.
    event = AuditEvent.objects.create(
        actor=actor,
        action=action,
        entity=entity,
        entity_id=entity_uuid,
        changes=changes,
        ip_address=ip_address,
        user_agent=user_agent or "",
        module=module or "unknown",
        previous_hash=previous_hash,
        is_valid=True,
    )
    event.refresh_from_db()
    current_hash = calculate_hash(
        timestamp=event.timestamp,
        actor_id=event.actor_id,
        action=event.action,
        entity=event.entity,
        entity_id=str(event.entity_id),
        changes=event.changes,
        previous_hash=event.previous_hash,
    )
    if event.current_hash != current_hash:
        # Update only if different (avoid recursive save).
        event.current_hash = current_hash
        event.save(update_fields=["current_hash"])

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
