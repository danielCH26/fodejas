"""Tests for CHG-206 migrations."""
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import TestCase

from apps.accounts.models import Role


class TestRolOfijurMigration(TestCase):
    """Test that R-OFIJUR role migration is idempotent."""

    def test_rol_ofijur_migration_on_disk(self):
        """Test that 0012_create_ofijur_role migration is registered on disk."""
        # disk_migrations is keyed by (app_label, migration_name) tuples
        self.assertIn(
            ("claims", "0012_create_ofijur_role"),
            MigrationLoader(connection).disk_migrations,
            "Migration 0012_create_ofijur_role must be registered",
        )

    def test_rol_ofijur_exists_after_migration(self):
        """Test that R-OFIJUR role exists in the database."""
        role = Role.objects.filter(code="R-OFIJUR").first()
        self.assertIsNotNone(role, "R-OFIJUR role should exist after migration")
        if role:
            self.assertEqual(role.name, "Oficina Jurídica")
            self.assertEqual(role.type, "interno")
            self.assertIn("apelaciones", role.description.lower())

    def test_rol_ofijur_has_correct_attributes(self):
        """Test that R-OFIJUR role has all required attributes."""
        role = Role.objects.get(code="R-OFIJUR")
        self.assertEqual(role.code, "R-OFIJUR")
        self.assertEqual(role.name, "Oficina Jurídica")
        self.assertEqual(role.type, "interno")
        self.assertIn("Oficina Jurídica", role.description)
        self.assertIn("apelaciones", role.description.lower())
        self.assertIn("2ª instancia", role.description.lower())

    def test_rol_ofijur_migration_is_idempotent(self):
        """Test that get_or_create is idempotent for the R-OFIJUR role."""
        initial_count = Role.objects.filter(code="R-OFIJUR").count()
        self.assertEqual(initial_count, 1, "Should have exactly one R-OFIJUR role")

        # Attempt to create with conflicting defaults — should not duplicate
        role1, created1 = Role.objects.get_or_create(
            code="R-OFIJUR",
            defaults={
                "name": "Different Name",
                "type": "externo",
                "description": "Different description",
            },
        )
        self.assertFalse(created1, "Should not create duplicate role")
        self.assertEqual(role1.name, "Oficina Jurídica", "Should keep original name")
        self.assertEqual(role1.type, "interno", "Should keep original type")

        final_count = Role.objects.filter(code="R-OFIJUR").count()
        self.assertEqual(final_count, 1, "Should still have exactly one R-OFIJUR role")
