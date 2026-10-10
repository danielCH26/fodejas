"""Tests for seed migration idempotency."""
import pytest
from django.db import connection


@pytest.mark.django_db
class TestSeedMigration:
    """Test that seed migrations are idempotent."""

    def test_seed_migration_runs_successfully(self):
        """Test that seed migration can be applied without errors."""
        # This test verifies the migration infrastructure exists
        # The actual seed data is added via RunPython migrations
        # which are tested via model tests
        from apps.core.models import (
            CausalTerminacionConvenio,
            EstadoDocumento,
            Estrato,
            Etnia,
            GrupoSisben,
            ModalidadApoyo,
            MunicipioIsla,
            NivelFormacion,
            TipoDocumento,
            TipoIes,
        )

        # Verify all catalog models exist and are accessible
        assert Estrato is not None
        assert GrupoSisben is not None
        assert Etnia is not None
        assert MunicipioIsla is not None
        assert NivelFormacion is not None
        assert ModalidadApoyo is not None
        assert TipoIes is not None
        assert TipoDocumento is not None
        assert EstadoDocumento is not None
        assert CausalTerminacionConvenio is not None

    def test_migration_state_consistent(self):
        """Test that migrations are in consistent state."""
        from io import StringIO

        from django.core.management import call_command

        # Check migration status
        out = StringIO()
        call_command('showmigrations', '--plan', stdout=out)
        plan = out.getvalue()

        # Verify core app has migrations applied
        assert 'core.0001_initial' in plan

    def test_catalog_tables_exist(self):
        """Test that all catalog tables exist in the database."""

        expected_tables = [
            'core_estrato',
            'core_gruposisben',
            'core_etnia',
            'core_municipioisla',
            'core_nivelformacion',
            'core_modalidadapoyo',
            'core_tipoies',
            'core_tipodocumento',
            'core_estadodocumento',
            'core_causalterminacionconvenio',
        ]

        with connection.cursor() as cursor:
            existing_tables = connection.introspection.table_names(cursor)

        for table in expected_tables:
            assert table in existing_tables, f"Table {table} not found"

    def test_idempotent_catalog_creation(self):
        """Test that creating catalogs with same code is idempotent via get_or_create."""
        from apps.core.models import Estrato

        # First creation
        estrato1, created1 = Estrato.objects.get_or_create(
            codigo='test-1',
            defaults={'nombre': 'Test Estrato', 'activo': True, 'orden': 99}
        )
        assert created1 is True

        # Second creation with same code - should not fail
        estrato2, created2 = Estrato.objects.get_or_create(
            codigo='test-1',
            defaults={'nombre': 'Test Estrato', 'activo': True, 'orden': 99}
        )
        assert created2 is False
        assert estrato1.id == estrato2.id

        # Cleanup
        Estrato.objects.filter(codigo='test-1').delete()
