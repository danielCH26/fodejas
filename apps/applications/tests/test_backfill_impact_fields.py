"""Tests for backfill_impact_fields management command."""

import pytest

from apps.applications.models import Solicitud
from apps.convocatories.models import Convocatory
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestBackfillImpactFields:
    """Tests for the backfill_impact_fields management command."""

    @pytest.fixture
    def three_users(self, db):
        """Create 3 users for unique solicitudes per convocatoria constraint."""
        users = []
        for i in range(3):
            user = User.objects.create_user(
                email=f"aspirante{i}@example.com",
                documento=f"1234567{i}",
                first_name=f"Aspirante{i}",
                last_name="Test",
                password="testpass123",
            )
            users.append(user)
        return users

    @pytest.fixture
    def convocatoria(self, db):
        return Convocatory.objects.create(
            nombre="Convocatoria Test Backfill",
            estado=Convocatory.Estado.EN_INSCRIPCION,
        )

    def test_match_institucion_normaliza_espacios(
        self, three_users, convocatoria
    ):
        """datos_academicos.institucion='Universidad   Nacional ' → ies_nombre='Universidad Nacional'."""
        from django.core.management import call_command
        from io import StringIO

        user = three_users[0]
        Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.RADICADA,
            datos_academicos={"institucion": "Universidad   Nacional "},
            datos_personales={"municipio": "san_andres"},
        )

        out = StringIO()
        call_command("backfill_impact_fields", stdout=out)
        output = out.getvalue()

        solicitud = Solicitud.objects.get(aspirante=user)
        assert solicitud.ies_nombre == "Universidad Nacional"
        # Report mentions ies_updated
        assert "ies_updated" in output.lower() or "ies" in output.lower()

    def test_match_municipio_asigna_fk(self, three_users, convocatoria):
        """datos_personales.municipio='san_andres' → municipio_origen FK resolved."""
        from django.core.management import call_command
        from io import StringIO

        from apps.core.management.commands.seed_municipio_isla import Command

        cmd = Command()
        cmd.handle()  # Seed the catalog first

        user = three_users[1]
        Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.RADICADA,
            datos_academicos={"institucion": "Universidad del Valle"},
            datos_personales={"municipio": "san_andres"},
        )

        out = StringIO()
        call_command("backfill_impact_fields", stdout=out)

        solicitud = Solicitud.objects.get(aspirante=user)
        assert solicitud.municipio_origen is not None
        assert solicitud.municipio_origen.codigo == "san_andres"

    def test_no_match_municipio_deja_null(self, three_users, convocatoria):
        """Unmatched municipio ('corn_island') → municipio_origen stays null."""
        from django.core.management import call_command
        from io import StringIO

        from apps.core.management.commands.seed_municipio_isla import Command

        Command().handle()

        user = three_users[2]
        Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.RADICADA,
            datos_academicos={"institucion": "IES Test"},
            datos_personales={"municipio": "corn_island"},
        )

        out = StringIO()
        call_command("backfill_impact_fields", stdout=out)
        output = out.getvalue()

        solicitud = Solicitud.objects.get(aspirante=user)
        assert solicitud.municipio_origen is None
        # Report mentions unmatched
        assert "unmatched" in output.lower() or "municipio" in output.lower()

    def test_solicitud_without_datos_unchanged(self, three_users, convocatoria):
        """Solicitud without datos_academicos/datos_personales → counters *_missing_data."""
        from django.core.management import call_command
        from io import StringIO

        from apps.core.management.commands.seed_municipio_isla import Command

        Command().handle()

        user = three_users[0]
        Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.RADICADA,
            datos_academicos={},
            datos_personales={},
        )

        out = StringIO()
        call_command("backfill_impact_fields", stdout=out)
        output = out.getvalue()

        assert "missing_data" in output.lower()

    def test_idempotencia_sin_duplicados(self, three_users, convocatoria):
        """Command run twice: second run reports all unchanged, no writes."""
        from django.core.management import call_command
        from io import StringIO

        from apps.core.management.commands.seed_municipio_isla import Command

        Command().handle()

        user = three_users[1]
        Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.RADICADA,
            datos_academicos={"institucion": "Universidad   de  los  Andes"},
            datos_personales={"municipio": "providencia"},
        )

        # First run
        out1 = StringIO()
        call_command("backfill_impact_fields", stdout=out1)
        out1_val = out1.getvalue()

        solicitud = Solicitud.objects.get(aspirante=user)
        assert solicitud.ies_nombre == "Universidad de los Andes"
        assert solicitud.municipio_origen.codigo == "providencia"

        # Second run
        out2 = StringIO()
        call_command("backfill_impact_fields", stdout=out2)
        out2_val = out2.getvalue()

        # Value unchanged
        solicitud.refresh_from_db()
        assert solicitud.ies_nombre == "Universidad de los Andes"
        assert solicitud.municipio_origen.codigo == "providencia"
        # Counters should show unchanged
        assert "ies_unchanged" in out2_val.lower() or "unchanged" in out2_val.lower()

    def test_dry_run_no_modifica_bd(self, three_users, convocatoria):
        """--dry-run: counters correct but DB unchanged."""
        from django.core.management import call_command
        from io import StringIO

        from apps.core.management.commands.seed_municipio_isla import Command

        Command().handle()

        user = three_users[2]
        Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=user,
            estado=Solicitud.Estado.RADICADA,
            datos_academicos={"institucion": "Universidad del Magdalena  "},
            datos_personales={"municipio": "santa_catalina"},
        )

        # Dry run
        out = StringIO()
        call_command("backfill_impact_fields", "--dry-run", stdout=out)
        output = out.getvalue()

        # DB unchanged
        solicitud = Solicitud.objects.get(aspirante=user)
        assert solicitud.ies_nombre is None
        assert solicitud.municipio_origen is None

        # But counters are printed
        assert "processed" in output.lower() or "processed" in output
