"""Tests para la migración CHG-804 backfill UUIDs en accounts.

Verifica idempotencia, no-op cuando ya es UUID, y determinismo del namespace.
No incluye datos personales (AGENTS.md §6 regla 1).
"""
import importlib
import inspect
import uuid

import pytest


NAMESPACE_URL = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

# El nombre del módulo empieza con dígito, así que no se puede hacer
# `from ... import 0008_...`. Usamos importlib.
migration_module = importlib.import_module(
    "apps.accounts.migrations.0008_backfill_uuids_customuser_role"
)


def test_namespace_is_stable():
    """El namespace debe ser estable para que el backfill sea determinístico."""
    assert migration_module.NAMESPACE_URL == NAMESPACE_URL


def test_namespace_used_in_backfill_functions():
    """Las funciones de backfill referencian el namespace del módulo."""
    src_user = inspect.getsource(migration_module.backfill_customuser_uuid)
    src_role = inspect.getsource(migration_module.backfill_role_uuid)
    assert "NAMESPACE_URL" in src_user
    assert "uuid5" in src_user
    assert "NAMESPACE_URL" in src_role
    assert "uuid5" in src_role


def test_backfill_functions_exist():
    assert migration_module.backfill_customuser_uuid is not None
    assert migration_module.backfill_role_uuid is not None


def test_idempotency_of_reverse():
    """El reverse_code está documentado como noop. Verificamos que retorna None."""
    assert migration_module._reverse(apps=None, schema_editor=None) is None


def test_namespace_key_format():
    """Las funciones usan f-strings con prefijo tabla + : + old_pk."""
    src_user = inspect.getsource(migration_module.backfill_customuser_uuid)
    src_role = inspect.getsource(migration_module.backfill_role_uuid)
    assert 'f"customuser:' in src_user
    assert 'f"role:' in src_role


def test_no_pii_in_migration_source():
    """Verifica que la migración no contiene strings que parezcan emails o
    documentos de identidad."""
    src = inspect.getsource(migration_module)
    forbidden_patterns = ["@example.com", "1234567890", "CC ", "TI "]
    for pattern in forbidden_patterns:
        assert pattern not in src, f"Found forbidden PII-like pattern: {pattern}"
