"""Tests para la migración CHG-804 backfill UUIDs en convocatories.

Espejo de apps/accounts/tests/test_migrations_0008_uuid.py pero para la
migración de Convocatory.
"""
import importlib
import inspect
import uuid

import pytest


NAMESPACE_URL = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

# El nombre del módulo empieza con dígito, así que no se puede hacer
# `from ... import 0003_...`. Usamos importlib.
migration_module = importlib.import_module(
    "apps.convocatories.migrations.0003_backfill_uuids_convocatory"
)


def test_namespace_is_stable():
    assert migration_module.NAMESPACE_URL == NAMESPACE_URL


def test_namespace_used_in_backfill_function():
    src = inspect.getsource(migration_module.backfill_convocatory_uuid)
    assert "NAMESPACE_URL" in src
    assert "uuid5" in src


def test_backfill_function_exists():
    assert migration_module.backfill_convocatory_uuid is not None


def test_idempotency_of_reverse():
    assert migration_module._reverse(apps=None, schema_editor=None) is None


def test_namespace_key_format():
    src = inspect.getsource(migration_module.backfill_convocatory_uuid)
    assert 'f"convocatory:' in src


def test_no_pii_in_migration_source():
    src = inspect.getsource(migration_module)
    forbidden_patterns = ["@example.com", "1234567890", "CC ", "TI "]
    for pattern in forbidden_patterns:
        assert pattern not in src, f"Found forbidden PII-like pattern: {pattern}"


def test_consistent_namespace_with_accounts_migration():
    """accounts/0008 y convocatories/0003 deben usar el mismo namespace para
    que cualquier forward-only repair sea simétrico."""
    accounts_migration = importlib.import_module(
        "apps.accounts.migrations.0008_backfill_uuids_customuser_role"
    )
    assert accounts_migration.NAMESPACE_URL == migration_module.NAMESPACE_URL
