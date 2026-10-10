"""Concurrency test for the audit chain (CHG-801 / AUD-003).

The hash chain head is protected by ``SELECT ... FOR UPDATE`` so two
concurrent writers serialize; without the lock both would read the
same ``previous_hash`` and the second writer's ``current_hash``
would collide with the unique index on the column.

We launch two threads that each write a small batch of audit
events inside their own ``transaction.atomic`` block. After both
threads finish, ``verify_chain()`` must report a valid chain and
the total event count must equal ``2 * n``.

Environment note: SQLite does not support real concurrency (it
takes a database-wide lock on writes). These tests skip on SQLite
because they would always raise ``OperationalError("database
table is locked")``. They pass on PostgreSQL, which is the
production target.
"""
from __future__ import annotations

import threading
import uuid
from typing import Any

import pytest
from django.db import connection, transaction

from apps.audit.models import AuditEvent
from apps.audit.services import log_audit_event, verify_chain


def _is_sqlite() -> bool:
    """Return True when the test database is SQLite.

    SQLite serializes writes with a database-wide lock, so the
    multi-threaded concurrency tests cannot meaningfully exercise
    the row-level lock. PostgreSQL (the production target) does
    support concurrent writers.
    """
    return connection.settings_dict.get("ENGINE", "").endswith("sqlite3")


@pytest.mark.skipif(
    _is_sqlite(),
    reason=(
        "SQLite takes a database-wide write lock; the row-level "
        "lock cannot be exercised from multiple threads. The "
        "production database is PostgreSQL."
    ),
)
@pytest.mark.django_db(transaction=True)
def test_concurrent_writes_serialize_through_lock():
    """Two threads each writing N rows; chain must remain valid."""
    AuditEvent.objects.all().delete()

    n = 5
    errors: list[BaseException] = []

    def writer(thread_id: int) -> None:
        try:
            for i in range(n):
                with transaction.atomic():
                    log_audit_event(
                        actor=None,
                        action="CREATE",
                        entity="ConcurrentModel",
                        entity_id=uuid.uuid4(),
                        changes={"thread": thread_id, "index": i},
                        module="test",
                    )
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)

    t1 = threading.Thread(target=writer, args=(1,))
    t2 = threading.Thread(target=writer, args=(2,))
    t1.start()
    t2.start()
    t1.join(timeout=30)
    t2.join(timeout=30)

    assert not t1.is_alive(), "thread 1 did not finish"
    assert not t2.is_alive(), "thread 2 did not finish"
    assert not errors, f"thread errors: {errors}"

    # Two threads × N writes must produce exactly 2*N events.
    assert AuditEvent.objects.count() == 2 * n

    # The chain must validate after concurrent commits.
    result = verify_chain()
    assert result["is_valid"] is True, (
        f"chain broken under concurrency: {result}"
    )
    assert result["break_point"] is None


@pytest.mark.skipif(
    _is_sqlite(),
    reason=(
        "SQLite takes a database-wide write lock; the row-level "
        "lock cannot be exercised from multiple threads. The "
        "production database is PostgreSQL."
    ),
)
@pytest.mark.django_db(transaction=True)
def test_concurrent_writes_no_unique_collision():
    """All ``current_hash`` values must be unique across writers.

    Without ``SELECT ... FOR UPDATE`` two writers could compute the
    same ``current_hash`` and trigger the unique-constraint error.
    The lock prevents this; if serialization were broken the second
    writer would either raise ``IntegrityError`` or write a row
    that fails ``verify_chain()``.
    """
    AuditEvent.objects.all().delete()

    n = 4
    barrier = threading.Barrier(2)

    def writer(_: Any) -> None:
        barrier.wait()
        for i in range(n):
            with transaction.atomic():
                log_audit_event(
                    actor=None,
                    action="UPDATE",
                    entity="CollisionModel",
                    entity_id=uuid.uuid4(),
                    changes={"index": i},
                    module="test",
                )

    threads = [threading.Thread(target=writer, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert AuditEvent.objects.count() == 2 * n
    distinct_hashes = (
        AuditEvent.objects.values_list("current_hash", flat=True).distinct().count()
    )
    assert distinct_hashes == 2 * n
