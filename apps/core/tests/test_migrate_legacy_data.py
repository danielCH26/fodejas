"""Tests for migrate_legacy_data management command (CHG-099).

Verifies:
- Dry-run doesn't write
- Apply creates records idempotently
- Validation aborts on bad schema
- PII detection aborts
"""
import csv
from pathlib import Path

from django.core.management import call_command
from django.core.management.base import CommandError

import pytest

from apps.accounts.models import CustomUser
from apps.applications.models import Solicitud
from apps.convocatories.models import Convocatory
from apps.governance.models import ActoAdministrativo, ListadoDefinitivo


SALT = "x" * 32


def _write_csv(path: Path, headers: list[str], rows: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


def _populate_legacy_source(source: Path):
    """Build a minimal valid legacy data set under `source`."""
    _write_csv(
        source / "convocatorias.csv",
        [
            "codigo", "nombre", "tipo", "periodo", "estado",
            "fecha_apertura", "fecha_cierre",
            "fecha_publicacion_preliminar", "fecha_publicacion_definitiva",
            "monto_semestre_smlmv", "duracion_maxima_semestres", "cupo_total",
            "modalidad_codigo",
        ],
        [
            {
                "codigo": "CONV-001-2025",
                "nombre": "anon-test-conv-001",
                "tipo": "cerrada",
                "periodo": "2025-1",
                "estado": "DEFINITIVA",
                "fecha_apertura": "2025-01-15",
                "fecha_cierre": "2025-03-15",
                "fecha_publicacion_preliminar": "2025-04-01T08:00:00",
                "fecha_publicacion_definitiva": "2025-04-15T08:00:00",
                "monto_semestre_smlmv": "5",
                "duracion_maxima_semestres": "10",
                "cupo_total": "50",
                "modalidad_codigo": "BECAS",
            },
        ],
    )
    _write_csv(
        source / "usuarios_legacy.csv",
        ["documento_hash", "email_hash", "role_codes", "is_active"],
        [
            {
                "documento_hash": "anon-test-doc-001",
                "email_hash": "anon-test-email-001",
                "role_codes": "R-ASPIRANTE",
                "is_active": "true",
            },
            {
                "documento_hash": "anon-test-doc-002",
                "email_hash": "anon-test-email-002",
                "role_codes": "R-JUNTA|R-CT",
                "is_active": "true",
            },
        ],
    )
    _write_csv(
        source / "solicitudes.csv",
        [
            "radicado", "convocatoria_codigo", "aspirante_documento_hash",
            "estado", "radicado_en", "datos_academicos_json",
            "datos_socioeconomicos_json", "datos_personales_json",
        ],
        [
            {
                "radicado": "RAD-2025-0001",
                "convocatoria_codigo": "CONV-001-2025",
                "aspirante_documento_hash": "anon-test-doc-001",
                "estado": "VERIFICADA",
                "radicado_en": "2025-03-15T10:00:00",
                "datos_academicos_json": "{}",
                "datos_socioeconomicos_json": "{}",
                "datos_personales_json": "{}",
            },
        ],
    )
    _write_csv(
        source / "actos_legacy.csv",
        [
            "numero", "tipo", "fecha_expedicion", "fecha_publicacion",
            "asunto", "considerandos_json", "resolutivo",
            "convocatoria_codigo", "firmantes_json", "estado",
        ],
        [
            {
                "numero": "FODEJAS-RESO-2025-00001",
                "tipo": "RESOLUCION",
                "fecha_expedicion": "2025-04-15",
                "fecha_publicacion": "2025-04-15T09:00:00",
                "asunto": "anon-test-asunto-reso",
                "considerandos_json": "[]",
                "resolutivo": "anon-test-resolutivo-reso",
                "convocatoria_codigo": "CONV-001-2025",
                "firmantes_json": "[]",
                "estado": "PUBLICADO",
            },
        ],
    )
    _write_csv(
        source / "listados_legacy.csv",
        [
            "convocatoria_codigo", "ranking_json",
            "fecha_publicacion", "acto_numero",
        ],
        [
            {
                "convocatoria_codigo": "CONV-001-2025",
                "ranking_json": "[]",
                "fecha_publicacion": "2025-04-15T09:00:00",
                "acto_numero": "FODEJAS-RESO-2025-00001",
            },
        ],
    )


@pytest.mark.django_db(transaction=True)
class TestMigrateLegacyData:
    def test_dry_run_creates_no_records(self, tmp_path, monkeypatch):
        source = tmp_path / "legacy"
        _populate_legacy_source(source)
        monkeypatch.setenv("LEGACY_DATA_SALT", SALT)

        call_command("migrate_legacy_data", f"--source={source}", "--dry-run")

        assert Convocatory.objects.count() == 0
        assert CustomUser.objects.count() == 0
        assert Solicitud.objects.count() == 0
        assert ActoAdministrativo.objects.count() == 0
        assert ListadoDefinitivo.objects.count() == 0

    def test_apply_creates_records(self, tmp_path, monkeypatch):
        source = tmp_path / "legacy"
        _populate_legacy_source(source)
        monkeypatch.setenv("LEGACY_DATA_SALT", SALT)

        call_command("migrate_legacy_data", f"--source={source}")

        assert Convocatory.objects.filter(codigo="CONV-001-2025").exists()
        assert CustomUser.objects.filter(documento="anon-test-doc-001").exists()
        assert CustomUser.objects.filter(documento="anon-test-doc-002").exists()
        assert Solicitud.objects.filter(radicado="RAD-2025-0001").exists()
        assert ActoAdministrativo.objects.filter(
            numero="FODEJAS-RESO-2025-00001"
        ).exists()
        assert ListadoDefinitivo.objects.filter(
            convocatoria__codigo="CONV-001-2025"
        ).exists()

    def test_idempotent(self, tmp_path, monkeypatch):
        source = tmp_path / "legacy"
        _populate_legacy_source(source)
        monkeypatch.setenv("LEGACY_DATA_SALT", SALT)

        call_command("migrate_legacy_data", f"--source={source}")
        counts_1 = {
            "conv": Convocatory.objects.count(),
            "users": CustomUser.objects.count(),
            "sols": Solicitud.objects.count(),
            "actos": ActoAdministrativo.objects.count(),
            "lists": ListadoDefinitivo.objects.count(),
        }

        call_command("migrate_legacy_data", f"--source={source}")
        counts_2 = {
            "conv": Convocatory.objects.count(),
            "users": CustomUser.objects.count(),
            "sols": Solicitud.objects.count(),
            "actos": ActoAdministrativo.objects.count(),
            "lists": ListadoDefinitivo.objects.count(),
        }
        assert counts_1 == counts_2

    def test_validation_aborts_on_missing_column(self, tmp_path, monkeypatch):
        source = tmp_path / "legacy"
        _populate_legacy_source(source)
        # Remove a required column from one CSV.
        bad = source / "convocatorias.csv"
        rows = list(csv.DictReader(open(bad, encoding="utf-8")))
        for r in rows:
            r.pop("modalidad_codigo")
        with open(bad, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "codigo", "nombre", "tipo", "periodo", "estado",
                    "fecha_apertura", "fecha_cierre",
                    "fecha_publicacion_preliminar",
                    "fecha_publicacion_definitiva",
                    "monto_semestre_smlmv",
                    "duracion_maxima_semestres",
                    "cupo_total",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        monkeypatch.setenv("LEGACY_DATA_SALT", SALT)
        with pytest.raises(CommandError, match="abortando"):
            call_command("migrate_legacy_data", f"--source={source}")

    def test_pii_detection_aborts(self, tmp_path, monkeypatch):
        source = tmp_path / "legacy"
        _populate_legacy_source(source)
        # Inject PII in a column that should be anonymized.
        bad = source / "solicitudes.csv"
        rows = list(csv.DictReader(open(bad, encoding="utf-8")))
        rows[0]["aspirante_documento_hash"] = "leaked@example.com"
        with open(bad, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        monkeypatch.setenv("LEGACY_DATA_SALT", SALT)
        with pytest.raises(CommandError, match="abortando"):
            call_command("migrate_legacy_data", f"--source={source}")

    def test_missing_salt_aborts(self, tmp_path, monkeypatch):
        source = tmp_path / "legacy"
        _populate_legacy_source(source)
        monkeypatch.delenv("LEGACY_DATA_SALT", raising=False)
        with pytest.raises(CommandError, match="LEGACY_DATA_SALT"):
            call_command("migrate_legacy_data", f"--source={source}")

    def test_skip_validation_skips_pii_check(self, tmp_path, monkeypatch):
        source = tmp_path / "legacy"
        _populate_legacy_source(source)
        # Inject PII but skip validation.
        bad = source / "solicitudes.csv"
        rows = list(csv.DictReader(open(bad, encoding="utf-8")))
        rows[0]["aspirante_documento_hash"] = "leaked@example.com"
        with open(bad, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        monkeypatch.setenv("LEGACY_DATA_SALT", SALT)
        call_command(
            "migrate_legacy_data",
            f"--source={source}",
            "--skip-validation",
            "--dry-run",
        )
        # If we got here without raising, the skip worked.

    def test_no_pii_in_test_source(self):
        """Belt-and-suspenders: assert the test fixtures themselves
        contain no raw PII (per AGENTS.md §6)."""
        import re

        test_root = Path(__file__).parent
        for csv_file in test_root.rglob("*.csv"):
            if csv_file.exists():
                content = csv_file.read_text(encoding="utf-8")
                # Only flag raw emails / documents / phones.
                for match in re.finditer(
                    r"[a-z]+@[a-z]+\.[a-z]+|^\d{7,10}$|^\d{10}$",
                    content,
                    flags=re.MULTILINE,
                ):
                    pytest.fail(
                        f"possible PII in test fixture {csv_file}: {match.group()!r}"
                    )
