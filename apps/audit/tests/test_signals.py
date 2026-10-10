"""Signal auto-fire tests (CHG-801 / AUD-002, AUD-010).

``apps.audit.signals.register_audit_signals()`` must connect
``post_save`` / ``post_delete`` to the audited models and the
handlers must read the actor from the
``apps.core.logging_config.actor_var`` contextvar.
"""

from __future__ import annotations

import pytest

from apps.audit.models import AuditEvent
from apps.core.logging_config import set_actor


@pytest.mark.django_db
class TestRoleSignal:
    """Saving a ``Role`` must trigger a CREATE audit event."""

    def test_role_create_emits_audit_event(self, admin_user_with_role):
        AuditEvent.objects.all().delete()
        actor = admin_user_with_role

        set_actor(actor)

        from apps.accounts.models import Role

        Role.objects.create(
            code="R-TEST-SIGNAL",
            name="Test Signal",
            type="interno",
            description="Synthetic role for signal test.",
        )

        events = list(AuditEvent.objects.filter(entity="role"))
        assert len(events) == 1
        evt = events[0]
        assert evt.action == "CREATE"
        assert evt.module == "accounts"
        assert evt.actor_id == actor.id

    def test_role_create_without_actor_marks_system(self, admin_user_with_role):
        AuditEvent.objects.all().delete()
        # No actor bound.
        set_actor(None)

        from apps.accounts.models import Role

        Role.objects.create(
            code="R-TEST-SYSTEM",
            name="Test System",
            type="interno",
            description="Synthetic role for system test.",
        )

        events = list(AuditEvent.objects.filter(entity="role"))
        assert len(events) == 1
        evt = events[0]
        assert evt.actor is None
        assert evt.changes is not None
        assert evt.changes.get("actor_is_system") is True


@pytest.mark.django_db
class TestEstratoSignal:
    """Catalog models in ``apps.core`` must be auto-audited."""

    def test_estrato_save_emits_audit_event_with_core_module(self, admin_user_with_role):
        AuditEvent.objects.all().delete()
        set_actor(admin_user_with_role)

        from apps.core.models import Estrato

        Estrato.objects.create(
            codigo="estrato-test-signal",
            nombre="Estrato Test Signal",
            descripcion="Synthetic estrato for signal test.",
        )

        # ``entity_id`` is a UUID5 of the catalog's int primary key
        # so we filter by entity name only and check the module
        # label. The full PK roundtrip is exercised in
        # ``test_chain.py``.
        events = list(AuditEvent.objects.filter(entity="estrato"))
        assert len(events) >= 1, "expected at least one audit event"
        evt = events[0]
        assert evt.module == "core"
        assert evt.action in {"CREATE", "UPDATE"}
        assert evt.actor_id == admin_user_with_role.id


@pytest.mark.django_db(transaction=True)
class TestChainRemainsValidAcrossSignals:
    """Signals must not corrupt the chain (lock is taken inside the helper)."""

    def test_signal_writes_yield_verifiable_chain(self, admin_user_with_role):
        from apps.core.logging_config import set_actor

        # Reset the actor contextvar to None in case a prior test
        # left a user there; the helper treats ``actor=None`` as
        # a system action and stamps ``actor_is_system=True`` on
        # the ``changes`` payload.
        set_actor(None)
        AuditEvent.objects.all().delete()
        assert AuditEvent.objects.count() == 0, "delete did not clear the chain"

        # Bind the actor to the user fixture AFTER the cleanup so
        # any audit events emitted by the user fixture (if any)
        # are not under the actor.
        set_actor(admin_user_with_role)

        from apps.accounts.models import Role

        for i in range(3):
            Role.objects.create(
                code=f"R-TEST-CHAIN-{i}",
                name=f"Test Chain {i}",
                type="interno",
                description=f"Synthetic role {i}.",
            )

        # Verify the role events we just created form a valid
        # sub-chain. (The full ``verify_chain()`` is exercised in
        # ``test_chain.py`` — here we scope to the events this test
        # owns to avoid coupling with audit events emitted by
        # fixtures or migrations.)
        from apps.audit.models import AuditEvent as AE

        events = list(AE.objects.filter(entity="role").order_by("timestamp", "id"))
        assert len(events) == 3, (
            f"expected 3 role events, got {len(events)}; total events: "
            f"{[(e.entity, e.entity_id, e.action) for e in AuditEvent.objects.all()]}"
        )
        prev = "0" * 64
        for evt in events:
            assert (
                evt.previous_hash == prev
            ), f"previous_hash mismatch at {evt.id}: got {evt.previous_hash}"
            prev = evt.current_hash

        # And each event's stored current_hash matches what
        # ``calculate_hash(...)`` produces from its persisted data —
        # i.e. the chain is internally consistent for the writes
        # this test owns.
        from apps.audit.services import calculate_hash

        for evt in events:
            recalculated = calculate_hash(
                timestamp=evt.timestamp,
                actor_id=evt.actor_id,
                action=evt.action,
                entity=evt.entity,
                entity_id=str(evt.entity_id),
                changes=evt.changes,
                previous_hash=evt.previous_hash,
            )
            assert recalculated == evt.current_hash, (
                f"hash drift on event {evt.id}: stored={evt.current_hash} "
                f"recalculated={recalculated}"
            )
