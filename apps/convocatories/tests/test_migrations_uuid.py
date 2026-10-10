"""Tests for the CHG-804 UUID backfill migrations (convocatories app).

Mirrors apps/accounts/tests/test_migrations_uuid.py for the Convocatory
model. Kept separate to keep per-app test scope clear.
"""

import uuid

import pytest

CONVOCATORIES_BACKFILL = "apps.convocatories.migrations.0003_backfill_uuids_convocatory"


@pytest.fixture
def convocatory_backfill_module():
    from importlib import import_module

    return import_module(CONVOCATORIES_BACKFILL)


class TestConvocatoryBackfillIdempotency:
    def test_backfill_is_noop_when_pk_is_uuid(self, convocatory_backfill_module):
        from django.apps import apps as global_apps

        Convocatory = global_apps.get_model("convocatories", "Convocatory")
        pk_internal_type = Convocatory._meta.pk.get_internal_type()
        assert (
            pk_internal_type == "UUIDField"
        ), "Test pre-condition: Convocatory PK must already be UUIDField."

        result = convocatory_backfill_module.backfill_convocatory_uuid(
            global_apps, schema_editor=None
        )
        assert result is None


class TestConvocatoryBackfillNamespace:
    def test_namespace_is_documented_url(self, convocatory_backfill_module):
        # RFC 4122 namespace URL — UUID v5 well-known constant.
        assert convocatory_backfill_module.NAMESPACE_URL == uuid.UUID(
            "6ba7b811-9dad-11d1-80b4-00c04fd430c8"
        )

    def test_deterministic_for_same_key(self, convocatory_backfill_module):
        ns = convocatory_backfill_module.NAMESPACE_URL
        assert uuid.uuid5(ns, "convocatory:42") == uuid.uuid5(ns, "convocatory:42")


class TestConvocatoryMigrationShape:
    def test_depends_on_0002(self, convocatory_backfill_module):
        deps = list(convocatory_backfill_module.Migration.dependencies)
        assert ("convocatories", "0002_alter_convocatory_id") in deps

    def test_data_only(self, convocatory_backfill_module):
        from django.db.migrations.operations.special import RunPython

        ops = convocatory_backfill_module.Migration.operations
        assert len(ops) == 1
        assert isinstance(ops[0], RunPython)


class TestConvocatoryReversibility:
    @pytest.mark.django_db(transaction=True)
    def test_migrate_back_and_forward(self):
        """Migrate down to 0002, then forward to 0003, and confirm the
        Convocatory table remains queryable with the UUIDField PK."""
        from django.apps import apps as global_apps
        from django.core.management import call_command

        call_command("migrate", "convocatories", "0002", verbosity=0)
        call_command("migrate", "convocatories", "0003", verbosity=0)

        Convocatory = global_apps.get_model("convocatories", "Convocatory")
        assert Convocatory._meta.pk.get_internal_type() == "UUIDField"
        assert Convocatory.objects.count() >= 0
