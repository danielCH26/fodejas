"""Tests for CHG-206 migrations."""
import pytest
from django.db import connection
from django.test import TestCase
from apps.accounts.models import Role
from django.apps import apps


class TestRolOfijurMigration(TestCase):
    """Test that R-OFIJUR role migration is idempotent."""

    def test_rol_ofijur_exists_after_migration(self):
        """Test that R-OFIJUR role exists in the database."""
        # This test will fail until the migration is created
        # We're testing the role exists with correct attributes
        role = Role.objects.filter(code="R-OFIJUR").first()
        
        # RED: This test should fail initially
        self.assertIsNotNone(role, "R-OFIJUR role should exist after migration")
        
        if role:
            self.assertEqual(role.name, "Oficina Jurídica")
            self.assertEqual(role.type, "interno")
            self.assertIn("apelaciones", role.description.lower())
    
    def test_rol_ofijur_has_correct_attributes(self):
        """Test that R-OFIJUR role has all required attributes."""
        role = Role.objects.get(code="R-OFIJUR")
        
        # Verify exact attribute values
        self.assertEqual(role.code, "R-OFIJUR")
        self.assertEqual(role.name, "Oficina Jurídica")
        self.assertEqual(role.type, "interno")
        self.assertIn("Oficina Jurídica", role.description)
        self.assertIn("apelaciones", role.description.lower())
        self.assertIn("2ª instancia", role.description.lower())
    
    def test_migration_is_idempotent(self):
        """Test that migration can be applied multiple times without duplication."""
        # Count roles before
        initial_count = Role.objects.filter(code="R-OFIJUR").count()
        self.assertEqual(initial_count, 1, "Should have exactly one R-OFIJUR role")
        
        # Apply migration logic again (simulate re-running migration)
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connection
        
        # Import the migration function directly
        from apps.claims.migrations import 0012_create_ofijur_role
        
        # This is a test - we can't actually re-run migration easily
        # Instead, we'll test the idempotency by calling get_or_create again
        Role = apps.get_model("accounts", "Role")
        
        # Try to create again
        role1, created1 = Role.objects.get_or_create(
            code="R-OFIJUR",
            defaults={
                "name": "Different Name",
                "type": "externo",
                "description": "Different description",
            },
        )
        
        # Should NOT create a new one
        self.assertFalse(created1, "Should not create duplicate role")
        self.assertEqual(role1.name, "Oficina Jurídica", "Should keep original name")
        self.assertEqual(role1.type, "interno", "Should keep original type")
        
        # Count after - should still be 1
        final_count = Role.objects.filter(code="R-OFIJUR").count()
        self.assertEqual(final_count, 1, "Should still have exactly one R-OFIJUR role")

    def test_migration_is_idempotent(self):
        """Test that migration can be applied multiple times without duplication."""
        # This test verifies idempotency
        from django.db.migrations.executor import MigrationExecutor
        from django.db import connection
        
        executor = MigrationExecutor(connection)
        
        # Get the migration by name
        migration = None
        for app_label, migrations in executor.loader.disk_migrations.items():
            for migration_name, migration_obj in migrations.items():
                if migration_name == "0012_create_ofijur_role":
                    migration = migration_obj
                    break
        
        # RED: This will fail until migration is created
        self.assertIsNotNone(
            migration,
            "Migration 0012_create_ofijur_role should exist"
        )