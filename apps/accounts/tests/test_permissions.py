"""Tests for permissions services."""
from django.contrib.auth.models import Group, Permission as AuthPermission
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.test import TestCase
from apps.accounts.models import CustomUser, Role, Permission, UserRole, RolePermission


class GetUserEffectivePermissionsTests(TestCase):
    """Test get_user_effective_permissions() service."""

    def setUp(self):
        """Set up test data."""
        # Clear cache before each test
        cache.clear()
        
        # Create test user
        self.user = CustomUser.objects.create(
            email="permissions@example.com",
            documento="555555555",
            first_name="Permissions",
            last_name="User"
        )
        
        # Create content type for auth permissions
        self.content_type = ContentType.objects.create(
            app_label="test_app",
            model="testmodel"
        )
    
    def test_get_user_effective_permissions_returns_user_permissions(self):
        """Test that get_user_effective_permissions returns user.get_all_permissions()."""
        # Given: a user with no special roles or permissions
        # (just their own user permissions if any)
        
        # When: we call get_user_effective_permissions
        # The function doesn't exist yet - this will fail (RED phase)
        from apps.accounts.services.permissions import get_user_effective_permissions
        result = get_user_effective_permissions(self.user)
        
        # Then: it should return user.get_all_permissions()
        expected = set(self.user.get_all_permissions())
        self.assertEqual(result, expected)

    def test_get_user_effective_permissions_includes_role_permissions(self):
        """Test that permissions from user's roles are included."""
        # Given: a user with a role that has permissions
        # Create a role with a group
        group = Group.objects.create(name="R-PERM")
        role = Role.objects.create(
            code="R-PERM",
            name="Permission Role",
            type="interno",
            group=group
        )
        
        # Create a Django auth permission
        auth_perm = AuthPermission.objects.create(
            content_type=self.content_type,
            codename="test_permission",
            name="Can test permission"
        )
        
        # Create our custom permission linked to auth permission
        custom_perm = Permission.objects.create(
            app_label="test_app",
            action="test_permission",
            auth_permission=auth_perm
        )
        
        # Link permission to role
        RolePermission.objects.create(role=role, permission=custom_perm)
        
        # Add auth permission to the group
        group.permissions.add(auth_perm)
        
        # Assign role to user using our service (which adds user to group)
        from apps.accounts.services.assignment import assign_role_to_user
        assign_role_to_user(self.user, role)
        
        # When: we call get_user_effective_permissions
        from apps.accounts.services.permissions import get_user_effective_permissions
        result = get_user_effective_permissions(self.user)
        
        # Then: it should include the permission from the role
        expected_perm = f"{auth_perm.content_type.app_label}.{auth_perm.codename}"
        self.assertIn(expected_perm, result)

    def test_get_user_effective_permissions_uses_caching(self):
        """Test that permissions are cached for performance."""
        # Given: a user
        # When: we call get_user_effective_permissions twice
        from apps.accounts.services.permissions import get_user_effective_permissions
        
        # First call should compute
        result1 = get_user_effective_permissions(self.user)
        
        # Modify user's groups to see if cache is used
        # (If cache is used, second call should return cached result, not recompute)
        # We'll test this by checking cache keys
        
        # Second call
        result2 = get_user_effective_permissions(self.user)
        
        # Then: results should be equal
        self.assertEqual(result1, result2)
        
        # And: there should be a cache entry
        cache_key = f"user_permissions_{self.user.id}"
        cached_result = cache.get(cache_key)
        self.assertIsNotNone(cached_result)
        self.assertEqual(set(cached_result), result1)

    def test_get_user_effective_permissions_cache_invalidates_on_role_change(self):
        """Test that cache is invalidated when user's roles change."""
        # Given: a user with cached permissions
        from apps.accounts.services.permissions import get_user_effective_permissions
        
        # Get initial permissions (will be cached)
        initial_perms = get_user_effective_permissions(self.user)
        
        # When: we assign a new role to the user
        group = Group.objects.create(name="R-NEW")
        role = Role.objects.create(
            code="R-NEW",
            name="New Role",
            type="interno",
            group=group
        )
        
        # Create and add a permission to the group
        auth_perm = AuthPermission.objects.create(
            content_type=self.content_type,
            codename="new_permission",
            name="Can new permission"
        )
        group.permissions.add(auth_perm)
        
        # Assign role to user using our service (which adds user to group)
        from apps.accounts.services.assignment import assign_role_to_user
        assign_role_to_user(self.user, role)
        
        # Refresh user from database to get new group memberships
        self.user.refresh_from_db()
        
        # Get fresh user instance to avoid any cached relationships
        fresh_user = CustomUser.objects.get(pk=self.user.pk)
        
        # Then: calling get_user_effective_permissions should return updated permissions
        # (cache should be invalidated or updated)
        updated_perms = get_user_effective_permissions(fresh_user)
        
        # The new permission should be included
        expected_perm = f"{auth_perm.content_type.app_label}.{auth_perm.codename}"
        self.assertIn(expected_perm, updated_perms)
        
        # And it should be different from initial permissions
        self.assertNotEqual(initial_perms, updated_perms)