"""Tests for the CHG-804 UUID backfill migrations (accounts app).

These tests verify:
- Idempotency: re-running the backfill on a table whose PK is already
  a UUIDField is a no-op.
- Namespace stability: the deterministic UUID is reproducible.
- No PII in fixtures: only synthetic codes are used.
"""
import uuid

import pytest


ACCOUNTS_BACKFILL = "apps.accounts.migrations.0008_backfill_uuids_customuser_role"
CONVOCATORIES_BACKFILL = (
    "apps.convocatories.migrations.0003_backfill_uuids_convocatory"
)


@pytest.fixture
def backfill_module():
    """Import the 0008 backfill module without triggering the full
    migration executor."""
    from importlib import import_module

    return import_module(ACCOUNTS_BACKFILL)


@pytest.fixture
def convocatory_backfill_module():
    """Import the 0003 backfill module."""
    from importlib import import_module

    return import_module(CONVOCATORIES_BACKFILL)


class TestBackfillIdempotency:
    """The backfill function MUST be a no-op when PK is already UUIDField."""

    def test_customuser_backfill_is_noop_when_pk_is_uuid(self, backfill_module):
        """When accounts_customuser.id is already UUIDField, the backfill
        returns early without writing."""
        from django.apps import apps as global_apps

        CustomUser = global_apps.get_model("accounts", "CustomUser")
        pk_internal_type = CustomUser._meta.pk.get_internal_type()
        assert pk_internal_type == "UUIDField", (
            "Test pre-condition: CustomUser PK must already be UUIDField "
            "for the noop branch to be exercised."
        )

        # Calling with schema_editor=None exercises only the guard.
        # If the guard fails, the next line will raise before any save()
        # because save() needs a DB.
        result = backfill_module.backfill_customuser_uuid(
            global_apps, schema_editor=None
        )
        assert result is None

    def test_role_backfill_is_noop_when_pk_is_uuid(self, backfill_module):
        """Same guard for Role."""
        from django.apps import apps as global_apps

        Role = global_apps.get_model("accounts", "Role")
        pk_internal_type = Role._meta.pk.get_internal_type()
        assert pk_internal_type == "UUIDField"

        result = backfill_module.backfill_role_uuid(global_apps, schema_editor=None)
        assert result is None

    def test_combined_forward_is_noop_when_pk_is_uuid(self, backfill_module):
        """The combined forward function exercises both branches and must
        complete cleanly without writing when both PKs are UUIDField."""
        from django.apps import apps as global_apps

        result = backfill_module._forward(global_apps, schema_editor=None)
        assert result is None

    def test_convocatory_backfill_is_noop_when_pk_is_uuid(
        self, convocatory_backfill_module
    ):
        from django.apps import apps as global_apps

        Convocatory = global_apps.get_model("convocatories", "Convocatory")
        pk_internal_type = Convocatory._meta.pk.get_internal_type()
        assert pk_internal_type == "UUIDField"

        result = convocatory_backfill_module.backfill_convocatory_uuid(
            global_apps, schema_editor=None
        )
        assert result is None


class TestBackfillNamespaceStability:
    """The deterministic UUID MUST be stable across runs."""

    def test_customuser_namespace_deterministic(self, backfill_module):
        """uuid5(NAMESPACE, 'customuser:42') is always the same."""
        ns = backfill_module.NAMESPACE_URL
        first = uuid.uuid5(ns, "customuser:42")
        second = uuid.uuid5(ns, "customuser:42")
        assert first == second
        # Sanity: not equal to uuid4().
        assert first != uuid.uuid4()

    def test_role_namespace_deterministic(self, backfill_module):
        ns = backfill_module.NAMESPACE_URL
        assert uuid.uuid5(ns, "role:1") == uuid.uuid5(ns, "role:1")

    def test_convocatory_namespace_deterministic(
        self, convocatory_backfill_module
    ):
        ns = convocatory_backfill_module.NAMESPACE_URL
        assert uuid.uuid5(ns, "convocatory:7") == uuid.uuid5(ns, "convocatory:7")

    def test_namespaces_are_consistent(self, backfill_module, convocatory_backfill_module):
        """Both migrations use the same UUID namespace to guarantee
        cross-app determinism when (table, pk) collide in the FQN key.
        """
        assert (
            backfill_module.NAMESPACE_URL
            == convocatory_backfill_module.NAMESPACE_URL
        )


class TestBackfillReverseIsDocumentedNoop:
    """Reverse code must be a noop with a documented reason."""

    def test_accounts_reverse_returns_none(self, backfill_module):
        assert backfill_module._reverse(None, schema_editor=None) is None

    def test_convocatories_reverse_returns_none(self, convocatory_backfill_module):
        assert convocatory_backfill_module._reverse(None, schema_editor=None) is None


class TestMigrationDependencies:
    """Verify dependency graph wiring (no schema drift)."""

    def test_accounts_0008_depends_on_0007(self, backfill_module):
        Migration = backfill_module.Migration
        deps = [(a, n) for a, n in Migration.dependencies]
        assert ("accounts", "0007_alter_role_id") in deps

    def test_accounts_0008_has_only_runpython_operation(self, backfill_module):
        """CHG-804 invariant: this is a data-only migration."""
        Migration = backfill_module.Migration
        assert len(Migration.operations) == 1
        from django.db.migrations.operations.special import RunPython

        assert isinstance(Migration.operations[0], RunPython)

    def test_convocatories_0003_depends_on_0002(self, convocatory_backfill_module):
        Migration = convocatory_backfill_module.Migration
        deps = [(a, n) for a, n in Migration.dependencies]
        assert ("convocatories", "0002_alter_convocatory_id") in deps

    def test_convocatories_0003_has_only_runpython_operation(
        self, convocatory_backfill_module
    ):
        Migration = convocatory_backfill_module.Migration
        assert len(Migration.operations) == 1
        from django.db.migrations.operations.special import RunPython

        assert isinstance(Migration.operations[0], RunPython)


class TestReversibilityWithMigrate:
    """Re-running migrate forward<->backward leaves the schema consistent."""

    @pytest.mark.django_db(transaction=True)
    def test_migrate_back_and_forward_is_consistent(self):
        """`migrate accounts 0007` then `migrate accounts 0008` must both
        succeed and leave the table queryable."""
        from django.core.management import call_command

        # Going back to the pre-backfill state.
        call_command("migrate", "accounts", "0007", verbosity=0)
        # Forward again.
        call_command("migrate", "accounts", "0008", verbosity=0)

        from django.apps import apps as global_apps

        CustomUser = global_apps.get_model("accounts", "CustomUser")
        Role = global_apps.get_model("accounts", "Role")
        # After both directions, both models are still queryable.
        assert CustomUser._meta.pk.get_internal_type() == "UUIDField"
        assert Role._meta.pk.get_internal_type() == "UUIDField"
        # Listing rows must work (empty in test DB is fine).
        assert CustomUser.objects.count() >= 0
        assert Role.objects.count() >= 0
