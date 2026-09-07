"""Tests for apps.core.migration_utils.validators (CHG-099)."""
import pytest

from apps.core.migration_utils.validators import (
    _is_pii,
    validate_fk_resolution,
    validate_no_pii,
    validate_schema,
)


SAMPLE_SALT = "x" * 32


class TestIsPii:
    @pytest.mark.parametrize(
        "raw",
        [
            "anon-test-123456789012",  # factory allowlist
            "anon-test-abc",
            "",
        ],
    )
    def test_safe_values(self, raw):
        assert _is_pii(raw) is False

    @pytest.mark.parametrize(
        "raw",
        [
            "anon-test-foobar",  # anon-test- prefix bypasses PII detection
            "anon-test-anything-here",
        ],
    )
    def test_allowlist_bypass(self, raw):
        # anon-test-* prefix bypasses PII detection — verify the allowlist.
        assert _is_pii(raw) is False

    @pytest.mark.parametrize(
        "raw",
        [
            "alguien@example.com",
            "user@gmail.com",
            "1234567890",
            "9876543",
            "3123456789",
        ],
    )
    def test_raw_pii_detected(self, raw):
        assert _is_pii(raw) is True


class TestValidateSchema:
    def test_ok(self, tmp_path):
        f = tmp_path / "ok.csv"
        f.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
        assert validate_schema(f, ["a", "b", "c"]) == []

    def test_missing_columns(self, tmp_path):
        f = tmp_path / "missing.csv"
        f.write_text("a,b\n1,2\n", encoding="utf-8")
        errors = validate_schema(f, ["a", "b", "c"])
        assert any("c" in e for e in errors)

    def test_extra_columns(self, tmp_path):
        f = tmp_path / "extra.csv"
        f.write_text("a,b,c,d\n1,2,3,4\n", encoding="utf-8")
        errors = validate_schema(f, ["a", "b", "c"])
        assert any("extra" in e for e in errors)

    def test_missing_file(self, tmp_path):
        f = tmp_path / "missing.csv"
        errors = validate_schema(f, ["a"])
        assert any("no encontrado" in e for e in errors)

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.csv"
        f.write_text("", encoding="utf-8")
        errors = validate_schema(f, ["a"])
        assert any("vacío" in e for e in errors)


class TestValidateNoPii:
    def test_ok(self, tmp_path):
        f = tmp_path / "ok.csv"
        f.write_text(
            "id,documento_hash\n"
            "1,anon-test-aaa\n"
            "2,anon-test-bbb\n",
            encoding="utf-8",
        )
        assert validate_no_pii(f, ["documento_hash"]) == []

    def test_detects_email(self, tmp_path):
        f = tmp_path / "bad.csv"
        f.write_text(
            "id,email_hash\n"
            "1,leaked@example.com\n",
            encoding="utf-8",
        )
        errors = validate_no_pii(f, ["email_hash"])
        assert any("PII crudo" in e for e in errors)

    def test_detects_documento(self, tmp_path):
        f = tmp_path / "bad.csv"
        f.write_text(
            "id,documento_hash\n"
            "1,1234567890\n",
            encoding="utf-8",
        )
        errors = validate_no_pii(f, ["documento_hash"])
        assert any("PII crudo" in e for e in errors)

    def test_detects_telefono(self, tmp_path):
        f = tmp_path / "bad.csv"
        f.write_text(
            "id,telefono_hash\n"
            "1,3123456789\n",
            encoding="utf-8",
        )
        errors = validate_no_pii(f, ["telefono_hash"])
        assert any("PII crudo" in e for e in errors)


class TestValidateFkResolution:
    def test_all_resolved(self):
        rows = [
            {"convocatoria_codigo": "CONV-001"},
            {"convocatoria_codigo": "CONV-002"},
        ]
        lookup = {"CONV-001", "CONV-002", "CONV-003"}
        assert validate_fk_resolution(rows, "convocatoria_codigo", lookup) == []

    def test_missing_fk(self):
        rows = [
            {"convocatoria_codigo": "CONV-001"},
            {"convocatoria_codigo": "CONV-MISSING"},
        ]
        lookup = {"CONV-001"}
        errors = validate_fk_resolution(rows, "convocatoria_codigo", lookup)
        assert any("CONV-MISSING" in e for e in errors)

    def test_empty_fk_value_ignored(self):
        rows = [{"convocatoria_codigo": ""}]
        lookup = {"CONV-001"}
        assert validate_fk_resolution(rows, "convocatoria_codigo", lookup) == []
