"""Tests for seed_municipio_isla management command."""

import pytest

from apps.core.models import MunicipioIsla


@pytest.mark.django_db
class TestSeedMunicipioIsla:
    """Tests for the seed_municipio_isla management command."""

    def test_seed_creates_three_rows(self):
        """First run: 3 rows created with exact codes/nombres/orden."""
        from django.core.management import call_command
        from io import StringIO

        out = StringIO()
        call_command("seed_municipio_isla", stdout=out)
        output = out.getvalue()

        assert MunicipioIsla.objects.count() == 3

        san_andres = MunicipioIsla.objects.get(codigo="san_andres")
        assert san_andres.nombre == "San Andrés"
        assert san_andres.orden == 1

        providencia = MunicipioIsla.objects.get(codigo="providencia")
        assert providencia.nombre == "Providencia"
        assert providencia.orden == 2

        santa_catalina = MunicipioIsla.objects.get(codigo="santa_catalina")
        assert santa_catalina.nombre == "Santa Catalina"
        assert santa_catalina.orden == 3

        # Output should mention creation
        assert "Created" in output or "exists" in output

    def test_seed_is_idempotent_no_duplicates(self):
        """Second run: still exactly 3 rows, no duplicates."""
        from django.core.management import call_command
        from io import StringIO

        # Seed twice
        call_command("seed_municipio_isla")
        call_command("seed_municipio_isla")

        # Must be exactly 3 rows
        assert MunicipioIsla.objects.count() == 3

        # Each code still resolves to exactly one row
        codes = list(MunicipioIsla.objects.values_list("codigo", flat=True))
        assert len(codes) == len(set(codes))

        # Codes still correct
        assert set(codes) == {"san_andres", "providencia", "santa_catalina"}

    def test_seed_default_manager_returns_activos(self):
        """Active manager returns only activo=True rows."""
        from django.core.management import call_command

        call_command("seed_municipio_isla")

        activos = MunicipioIsla.activos.all()
        assert activos.count() == 3
        assert all(m.activo for m in activos)
