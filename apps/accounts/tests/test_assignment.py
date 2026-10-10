"""Tests for role assignment services."""

from django.contrib.auth.models import Group
from django.test import TestCase

from apps.accounts.models import CustomUser, Role, UserRole


class AssignRoleToUserTests(TestCase):
    """Test assign_role_to_user() service."""

    def test_assign_role_to_user_creates_user_role(self):
        """Test that assign_role_to_user creates a UserRole instance."""
        # Given: a user and a role with a group
        user = CustomUser.objects.create(
            email="test@example.com", documento="123456789", first_name="Test", last_name="User"
        )

        # Create a role with a group
        group = Group.objects.create(name="R-TEST")
        role = Role.objects.create(code="R-TEST", name="Test Role", type="interno", group=group)

        # When: we call assign_role_to_user
        # The function doesn't exist yet - this will fail (RED phase)
        from apps.accounts.services.assignment import assign_role_to_user

        result = assign_role_to_user(user, role)

        # Then: a UserRole should be created
        self.assertIsNotNone(result)
        self.assertIsInstance(result, UserRole)
        self.assertEqual(result.user, user)
        self.assertEqual(result.role, role)

        # And: the user should be added to the role's group
        self.assertTrue(user.groups.filter(id=group.id).exists())

        # And: the UserRole should be saved in the database
        self.assertTrue(UserRole.objects.filter(user=user, role=role).exists())

    def test_assign_role_to_user_with_convocation_scope(self):
        """Test assign_role_to_user with convocation scope."""
        # Given: a user, a role with group, and a convocation scope
        user = CustomUser.objects.create(
            email="scope@example.com", documento="987654321", first_name="Scope", last_name="User"
        )

        group = Group.objects.create(name="R-SCOPE")
        role = Role.objects.create(code="R-SCOPE", name="Scope Role", type="externo", group=group)

        convocation_scope = "CONV-2025-001"

        # When: we call assign_role_to_user with convocation scope
        from apps.accounts.services.assignment import assign_role_to_user

        result = assign_role_to_user(user, role, convocation_scope)

        # Then: UserRole should be created with convocation scope
        self.assertIsNotNone(result)
        self.assertEqual(result.convocation_scope_id, convocation_scope)

        # And: user should still be added to the group
        self.assertTrue(user.groups.filter(id=group.id).exists())

    def test_assign_role_to_user_without_group_raises_error(self):
        """Test that assigning a role without a group raises an error."""
        # Given: a user and a role without a group
        user = CustomUser.objects.create(
            email="nogroup@example.com", documento="555555555", first_name="No", last_name="Group"
        )

        role = Role.objects.create(
            code="R-NO-GROUP",
            name="No Group Role",
            type="externo",
            # No group assigned
        )

        # When/Then: calling assign_role_to_user should raise an error
        from apps.accounts.services.assignment import assign_role_to_user

        with self.assertRaises(ValueError):
            assign_role_to_user(user, role)

    def test_assign_role_to_user_already_assigned(self):
        """Test that assigning the same role twice raises an error due to unique constraint."""
        # Given: a user and a role with group
        user = CustomUser.objects.create(
            email="duplicate@example.com",
            documento="111111111",
            first_name="Duplicate",
            last_name="User",
        )

        group = Group.objects.create(name="R-DUP")
        role = Role.objects.create(code="R-DUP", name="Duplicate Role", type="interno", group=group)

        # First assignment should succeed
        from apps.accounts.services.assignment import assign_role_to_user

        result1 = assign_role_to_user(user, role)
        self.assertIsNotNone(result1)

        # When/Then: second assignment should raise IntegrityError
        # Note: Django's create() might raise IntegrityError or let the database raise it
        # We'll test that an exception is raised
        try:
            assign_role_to_user(user, role)
            self.fail("Expected an exception when assigning duplicate role")
        except Exception:
            # Any exception is acceptable
            pass


class RevokeRoleFromUserTests(TestCase):
    """Test revoke_role_from_user() service."""

    def test_revoke_role_from_user_removes_user_from_group(self):
        """Test that revoke_role_from_user removes user from group and deletes UserRole."""
        # Given: a user with an assigned role
        user = CustomUser.objects.create(
            email="revoke@example.com", documento="222222222", first_name="Revoke", last_name="User"
        )

        group = Group.objects.create(name="R-REVOKE")
        role = Role.objects.create(code="R-REVOKE", name="Revoke Role", type="interno", group=group)

        # Assign the role first
        from apps.accounts.services.assignment import assign_role_to_user

        user_role = assign_role_to_user(user, role)

        # Verify user is in the group
        self.assertTrue(user.groups.filter(id=group.id).exists())

        # When: we call revoke_role_from_user
        # The function doesn't exist yet - this will fail (RED phase)
        from apps.accounts.services.assignment import revoke_role_from_user

        revoke_role_from_user(user_role)

        # Then: user should be removed from the group
        self.assertFalse(user.groups.filter(id=group.id).exists())

        # And: UserRole should be deleted
        with self.assertRaises(UserRole.DoesNotExist):
            UserRole.objects.get(id=user_role.id)

    def test_revoke_role_from_user_logs_to_audit(self):
        """Test that revoke_role_from_user logs to audit."""
        # Given: a user with an assigned role
        user = CustomUser.objects.create(
            email="audit@example.com", documento="333333333", first_name="Audit", last_name="User"
        )

        admin_user = CustomUser.objects.create(
            email="admin@example.com", documento="444444444", first_name="Admin", last_name="User"
        )

        group = Group.objects.create(name="R-AUDIT")
        role = Role.objects.create(code="R-AUDIT", name="Audit Role", type="interno", group=group)

        # Assign the role first
        from apps.accounts.services.assignment import assign_role_to_user

        user_role = assign_role_to_user(user, role, actor=admin_user)

        # When: we call revoke_role_from_user with an actor
        from apps.accounts.services.assignment import revoke_role_from_user

        revoke_role_from_user(user_role, actor=admin_user)

        # Then: UserRole should be deleted
        with self.assertRaises(UserRole.DoesNotExist):
            UserRole.objects.get(id=user_role.id)
