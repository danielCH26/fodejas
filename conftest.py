"""
Root conftest — ephemeral test database.

Root cause of cascade failures (29+34):
  pytest-django copies the persistent dev SQLite (db.sqlite3) into the
  test DB at session start.  That copy already contains orphan
  AuditEvent rows from previous pytest sessions.  Within a single run,
  tests using @pytest.mark.django_db(transaction=True) commit data
  (audit events, treasury rows) that subsequent tests' fixture setups
  then collide with.

Fix: use a shared in-memory SQLite (file::memory:?cache=shared) that
  is created fresh for each pytest session.  No data persists between
  sessions, and the DB is empty at session start.

  SQLite URI format: file:testdb?mode=memory&cache=shared&uri=true
  - :memory: gives an ephemeral in-memory DB
  - cache=shared allows multiple connections to see the same DB
  - uri=true requires the full URI to open the shared cache

Tradeoff: the shared cache persists for the duration of the session,
  so transaction=True tests within the same session still share committed
  data.  This is a known limitation; tests that need complete isolation
  should be run in separate processes or against PostgreSQL.  The key
  improvement is that the DB is clean at session start (no db.sqlite3
  contamination) and gone at session end.
"""

from __future__ import annotations

import pytest


@pytest.fixture(scope="session")
def django_db_modify_db_settings(
    django_db_modify_db_settings_parallel_suffix: None,  # noqa: ARG001
) -> None:
    """Override test database to ephemeral in-memory SQLite.

    The ``parallel_suffix`` parameter is a required dependency from
    pytest-django; we pass it through unchanged.
    """
    from django.conf import settings

    # Keep FileField uploads out of the repository: route media to a
    # session temp dir (upload-path tests would otherwise litter the
    # working tree, e.g. condonation/payments/comprobante_*.pdf).
    import tempfile

    settings.MEDIA_ROOT = tempfile.mkdtemp(prefix="fodejas-test-media-")

    # Speed: tests create many users via fixtures; default PBKDF2
    # (720k iterations) dominated runtime. MD5 is test-only.
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

    # Use SQLite URI with shared cache so multiple connections
    # (setup connection, test connection) share the same DB.
    settings.DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": "file:testdb?mode=memory&cache=shared&uri=true",
        "ATOMIC_REQUESTS": False,
        "AUTOCOMMIT": True,
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "OPTIONS": {
            "check_same_thread": False,
        },
    }


@pytest.fixture(autouse=True)
def _reset_actor_contextvar():
    """Reset the audit actor contextvar at every test boundary.

    Root cause of the cascade teardown errors: ``set_actor(user)``
    leaks across tests in the same thread. A later test whose
    fixtures/signals fire ``log_audit_event`` then inserts an
    ``AuditEvent`` with ``actor_id`` pointing at a user that was
    rolled back (TestCase) or truncated (TransactionTestCase) —
    the orphan row trips ``check_constraints()`` at teardown and
    ``FOREIGN KEY constraint failed`` at setup of the next test.
    Resetting at both boundaries guarantees no test inherits
    another test's actor. Production code is unaffected.
    """
    from apps.core.logging_config import set_actor

    set_actor(None)
    yield
    set_actor(None)
