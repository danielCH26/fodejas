"""Tests for apps.core.migration_utils.anonymize (CHG-099)."""
import os
from unittest.mock import patch

import pytest

from apps.core.migration_utils import anonymize


class TestAnonymizeHash:
    def test_returns_12_hex_chars(self):
        result = anonymize.anonymize_hash("test-value", salt="a" * 32)
        assert len(result) == 12
        assert all(c in "0123456789abcdef" for c in result)

    def test_is_deterministic(self):
        a = anonymize.anonymize_hash("same-input", salt="b" * 32)
        b = anonymize.anonymize_hash("same-input", salt="b" * 32)
        assert a == b

    def test_different_inputs_produce_different_hashes(self):
        a = anonymize.anonymize_hash("input-one", salt="c" * 32)
        b = anonymize.anonymize_hash("input-two", salt="c" * 32)
        assert a != b

    def test_different_salts_produce_different_hashes(self):
        a = anonymize.anonymize_hash("same", salt="salt-one-aaaaaaaaaaaa")
        b = anonymize.anonymize_hash("same", salt="salt-two-bbbbbbbbbbbb")
        assert a != b

    def test_raises_without_salt(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="se requiere salt"):
                anonymize.anonymize_hash("x")

    def test_raises_with_short_salt(self):
        with patch.dict(os.environ, {"LEGACY_DATA_SALT": "short"}):
            with pytest.raises(ValueError, match="demasiado corto"):
                anonymize.anonymize_hash("x")

    def test_uses_env_var_when_no_explicit_salt(self):
        with patch.dict(os.environ, {"LEGACY_DATA_SALT": "x" * 32}):
            a = anonymize.anonymize_hash("foo")
            b = anonymize.anonymize_hash("foo")
            assert a == b  # deterministic from env salt

    def test_handles_unicode(self):
        result = anonymize.anonymize_hash(
            "Pepita Pérez García", salt="y" * 32
        )
        assert len(result) == 12


class TestAnonymizeOptional:
    def test_none_returns_none(self):
        assert anonymize.anonymize_optional(None, salt="z" * 32) is None

    def test_empty_returns_none(self):
        assert anonymize.anonymize_optional("", salt="z" * 32) is None
        assert anonymize.anonymize_optional("   ", salt="z" * 32) is None

    def test_value_returns_hash(self):
        result = anonymize.anonymize_optional("someone@example.com", salt="z" * 32)
        assert result is not None
        assert len(result) == 12


class TestAnonymizeJson:
    def test_recursively_anonymizes_strings(self):
        salt = "w" * 32
        data = {
            "nombre": "Juan",
            "documento": "1234567890",
            "hijos": [{"nombre": "Ana"}, {"nombre": "Beto"}],
            "metadata": {"fecha": "2026-01-01", "cantidad": 5},
        }
        result = anonymize.anonymize_json(data, salt)
        # Top-level strings hashed.
        assert isinstance(result["nombre"], str)
        assert result["nombre"] != "Juan"
        # Integers pass through.
        assert result["metadata"]["cantidad"] == 5
        # Nested strings hashed.
        assert result["hijos"][0]["nombre"] != "Ana"

    def test_handles_none_and_booleans(self):
        salt = "w" * 32
        data = {"a": None, "b": True, "c": False, "d": 0}
        result = anonymize.anonymize_json(data, salt)
        assert result["a"] is None
        assert result["b"] is True
        assert result["c"] is False
        assert result["d"] == 0
