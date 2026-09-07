"""Concurrency tests for ``TreasuryService`` (CHG-802 / AUD-004).

Two threads racing on the same ``authorize(auth_id, user,
'president')`` MUST serialize: exactly one wins, the other
gets a clean ``ValueError`` (or sees the row in
``AUTORIZADO`` state).

NOTE: SQLite does not support row-level locking the same way
PostgreSQL does — concurrent writers see ``OperationalError:
database table is locked`` instead of serializing. We skip
these tests on SQLite and run them on PostgreSQL, which is the
production target (CHG-801 used the same skipif pattern for
``audit/tests/test_concurrency.py``).
"""
from __future__ import annotations

import threading

import pytest
from django.db import connection

from apps.treasury.models import DisbursementAuthorization
from apps.treasury.services import TreasuryService


def _is_sqlite() -> bool:
    return connection.vendor == "sqlite"


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(
    _is_sqlite(),
    reason="SQLite lacks row-level locks; concurrency tests require PostgreSQL.",
)
class TestAuthorizeConcurrency:
    def test_two_threads_authorize_one_wins(self, auth_factory, user_factory):
        """Two threads both call ``authorize(..., 'president')`` on the same row."""
        auth = auth_factory(status=DisbursementAuthorization.Status.PENDIENTE)

        results: list[tuple[str, BaseException | DisbursementAuthorization]] = []
        barrier = threading.Barrier(2)

        def attempt():
            user = user_factory()
            try:
                barrier.wait(timeout=5)
                result = TreasuryService.authorize(
                    auth.id, user, "president"
                )
                results.append(("ok", result))
            except BaseException as exc:  # noqa: BLE001 - we want any error type
                results.append(("err", exc))

        t1 = threading.Thread(target=attempt)
        t2 = threading.Thread(target=attempt)
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        oks = [r for tag, r in results if tag == "ok"]
        errs = [r for tag, r in results if tag == "err"]

        assert len(oks) == 1, f"expected 1 success, got {len(oks)} ({results})"
        assert len(errs) == 1, f"expected 1 failure, got {len(errs)} ({results})"
        assert isinstance(errs[0], ValueError), (
            f"loser should raise ValueError; got {type(errs[0]).__name__}: {errs[0]}"
        )

        auth.refresh_from_db()
        assert auth.authorized_by_president is not None


@pytest.mark.django_db
class TestAuthorizeBasic:
    """Sanity tests that work on SQLite (no concurrency)."""

    def test_authorize_president_sets_field(self, auth_factory, user_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.PENDIENTE)
        user = user_factory()
        result = TreasuryService.authorize(auth.id, user, "president")
        assert result.authorized_by_president_id == user.id

    def test_authorize_twice_raises(self, auth_factory, user_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.PENDIENTE)
        u1 = user_factory()
        u2 = user_factory()
        TreasuryService.authorize(auth.id, u1, "president")
        with pytest.raises(ValueError):
            TreasuryService.authorize(auth.id, u2, "president")
