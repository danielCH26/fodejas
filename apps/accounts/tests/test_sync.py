"""Tests for sync services."""
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission as AuthPermission
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from apps.accounts.models import Permission, Role


class SyncRoleToGroupTests(TestCase):
    """Test sync_role_to_group() service."""

    def test_sync_role_to_group_creates_group_when_none_exists(self):
        """Test that sync creates a group when role doesn't have one."""
        # Given: a role without a group
        role = Role.objects.create(
            code="R-TEST",
            name="Test Role",
            type="interno",
            description="Test role for sync"
        )
        # No group exists yet

        # When: we call sync_role_to_group
        # The function doesn't exist yet - this will fail
        from apps.accounts.services.sync import sync_role_to_group
        result = sync_role_to_group(role)

        # Then: a group should be created and linked to the role
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "R-TEST")
        role.refresh_from_db()
        self.assertEqual(role.group, result)

    def test_sync_role_to_group_returns_existing_group(self):
        """Test that sync returns existing group when role already has one."""
        # Given: a role with an existing group
        group = Group.objects.create(name="R-EXISTING")
        role = Role.objects.create(
            code="R-EXISTING",
            name="Existing Role",
            type="interno",
            description="Role with existing group",
            group=group
        )

        # When: we call sync_role_to_group
        from apps.accounts.services.sync import sync_role_to_group
        result = sync_role_to_group(role)

        # Then: the existing group should be returned
        self.assertEqual(result, group)
        self.assertEqual(result.name, "R-EXISTING")

    def test_sync_role_to_group_handles_group_name_conflict(self):
        """Test that sync handles case where group name already exists in auth.Group."""
        # Given: a group with the same name already exists
        existing_group = Group.objects.create(name="R-CONFLICT")
        role = Role.objects.create(
            code="R-CONFLICT",
            name="Conflict Role",
            type="interno",
            description="Role with name conflict"
        )

        # When: we call sync_role_to_group
        from apps.accounts.services.sync import sync_role_to_group
        result = sync_role_to_group(role)

        # Then: should return the existing group and link it to role
        self.assertEqual(result, existing_group)
        role.refresh_from_db()
        self.assertEqual(role.group, existing_group)


class SyncPermissionToAuthPermTests(TestCase):
    """Test sync_permission_to_auth_perm() service."""

    def test_sync_permission_to_auth_perm_creates_auth_permission(self):
        """Test that sync creates auth.Permission for custom permission."""
        # Given: a custom permission without auth_permission
        permission = Permission.objects.create(
            app_label="applications",
            action="add_solicitud",
            convocation_scope_id=None,
            stage=None
        )

        # When: we call sync_permission_to_auth_perm
        # The function doesn't exist yet - this will fail
        from apps.accounts.services.sync import sync_permission_to_auth_perm
        result = sync_permission_to_auth_perm(permission)

        # Then: an auth.Permission should be created and linked
        self.assertIsNotNone(result)
        self.assertEqual(result.codename, "add_solicitud")
        self.assertEqual(result.content_type.app_label, "applications")
        permission.refresh_from_db()
        self.assertEqual(permission.auth_permission, result)

    def test_sync_permission_to_auth_perm_returns_existing_auth_permission(self):
        """Test that sync returns existing auth.Permission when already linked."""
        # Given: a custom permission with existing auth_permission
        content_type = ContentType.objects.get_for_model(Permission)
        auth_perm = AuthPermission.objects.create(
            content_type=content_type,
            codename="add_solicitud",
            name="Can add solicitud"
        )
        permission = Permission.objects.create(
            app_label="applications",
            action="add_solicitud",
            convocation_scope_id=None,
            stage=None,
            auth_permission=auth_perm
        )

        # When: we call sync_permission_to_auth_perm
        from apps.accounts.services.sync import sync_permission_to_auth_perm
        result = sync_permission_to_auth_perm(permission)

        # Then: existing auth_permission should be returned
        self.assertEqual(result, auth_perm)

    def test_sync_permission_to_auth_perm_handles_scope_and_stage(self):
        """Test that sync handles permissions with convocation scope and stage."""
        # Given: a scoped permission
        permission = Permission.objects.create(
            app_label="applications",
            action="view_solicitud",
            convocation_scope_id="CONV-2025-001",
            stage="revision"
        )

        # When: we call sync_permission_to_auth_perm
        from apps.accounts.services.sync import sync_permission_to_auth_perm
        result = sync_permission_to_auth_perm(permission)

        # Then: auth.Permission should be created
        self.assertIsNotNone(result)
        # Note: auth.Permission doesn't store scope/stage, so codename
        # should include app_label and action only
        self.assertEqual(result.codename, "view_solicitud")
        self.assertEqual(result.content_type.app_label, "applications")
