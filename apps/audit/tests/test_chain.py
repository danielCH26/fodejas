"""Hash chain integrity tests (CHG-801 / AUD-001, AUD-003)."""
from __future__ import annotations

import uuid

import pytest
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import (
    calculate_hash,
    log_audit_event,
    verify_chain,
)


@pytest.mark.django_db
class TestHashCalculation:
    """``calculate_hash(...)`` is the primitive — must be deterministic."""

    def test_returns_64_hex_chars(self):
        ts = timezone.now()
        digest = calculate_hash(
            timestamp=ts,
            actor_id=None,
            action="CREATE",
            entity="TestModel",
            entity_id=uuid.uuid4(),
            changes={"k": "v"},
            previous_hash="0" * 64,
        )
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)

    def test_same_inputs_produce_same_hash(self):
        ts = timezone.now()
        eid = uuid.uuid4()
        h1 = calculate_hash(
            timestamp=ts,
            actor_id=1,
            action="CREATE",
            entity="TestModel",
            entity_id=eid,
            changes={"k": "v"},
            previous_hash="0" * 64,
        )
        h2 = calculate_hash(
            timestamp=ts,
            actor_id=1,
            action="CREATE",
            entity="TestModel",
            entity_id=eid,
            changes={"k": "v"},
            previous_hash="0" * 64,
        )
        assert h1 == h2

    def test_different_inputs_produce_different_hashes(self):
        ts = timezone.now()
        h1 = calculate_hash(
            timestamp=ts,
            actor_id=1,
            action="CREATE",
            entity="TestModel",
            entity_id=uuid.uuid4(),
            changes={"k": "v1"},
            previous_hash="0" * 64,
        )
        h2 = calculate_hash(
            timestamp=ts,
            actor_id=1,
            action="CREATE",
            entity="TestModel",
            entity_id=uuid.uuid4(),
            changes={"k": "v2"},
            previous_hash="0" * 64,
        )
        assert h1 != h2


@pytest.mark.django_db(transaction=True)
class TestChainLinkage:
    """Three consecutive writes must produce a verifiable chain.

    Uses ``transaction=True`` (TransactionTestCase mode) so each
    write commits and is immediately visible to subsequent
    reads. The default TestCase mode wraps the test in a single
    outer transaction that interacts oddly with the audit helper's
    nested ``@transaction.atomic`` and the shared-cache ``:memory:``
    SQLite database, producing intermittent hash-mismatch errors
    on this specific backend. PostgreSQL is unaffected.
    """

    def test_three_consecutive_events_form_valid_chain(self):
        # Clean up any audit events left behind by migrations
        # (e.g. the R-OFIJUR role creation in
        # claims.0012_create_ofijur_role fires the audit signal).
        # Migrations run before TransactionTestCase tests in the
        # same process and their commits persist.
        pre_count = AuditEvent.objects.count()
        if pre_count:
            AuditEvent.objects.all().delete()
        assert AuditEvent.objects.count() == 0, (
            "chain not empty after delete"
        )

        # Force distinct timestamps on SQLite (which stores
        # datetimes to microsecond precision).
        import time as _time

        entity_ids = []
        for _ in range(3):
            entity_ids.append(uuid.uuid4())
            _time.sleep(0.002)

        events = []
        for i, eid in enumerate(entity_ids):
            evt = log_audit_event(
                actor=None,
                action="CREATE",
                entity="TestModel",
                entity_id=eid,
                changes={"index": i},
                module="test",
            )
            events.append(evt)

        # Each event's previous_hash must point at the prior event's
        # current_hash — the chain is single-linked in time order.
        prev = "0" * 64
        for evt in events:
            assert evt.previous_hash == prev, (
                f"previous_hash mismatch at event {evt.id}: "
                f"got {evt.previous_hash}, expected {prev}"
            )
            prev = evt.current_hash

        result = verify_chain()
        assert result["is_valid"] is True, (
            f"chain broken after 3 writes: {result}; "
            f"events written: {[e.id for e in events]}; "
            f"timestamps: {[e.timestamp.isoformat() for e in events]}"
        )
        assert result["break_point"] is None
        assert result["last_valid_hash"] == events[-1].current_hash

    def test_first_event_uses_zeros_as_previous_hash(self):
        AuditEvent.objects.all().delete()
        event = log_audit_event(
            actor=None,
            action="CREATE",
            entity="FirstModel",
            entity_id=uuid.uuid4(),
            changes={"first": True},
            module="test",
        )
        assert event.previous_hash == "0" * 64

    def test_empty_chain_is_valid(self):
        AuditEvent.objects.all().delete()
        result = verify_chain()
        assert result["is_valid"] is True
        assert result["last_valid_hash"] == "0" * 64
        assert result["break_point"] is None


@pytest.mark.django_db
class TestActorSentinel:
    """``actor=None`` writes SHALL carry the system sentinel in metadata."""

    def test_system_event_actor_is_marked(self):
        AuditEvent.objects.all().delete()
        event = log_audit_event(
            actor=None,
            action="CREATE",
            entity="SystemModel",
            entity_id=uuid.uuid4(),
            changes={"reason": "background task"},
            module="test",
        )
        assert event.actor is None
        assert event.changes["actor_is_system"] is True
