"""Tests for accounts admin views."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.models import Role, UserRole

User = get_user_model()


class AdminViewTestMixin:
    """Mixin with helper methods for admin view tests."""

    def create_admin_user(self):
        """Create a user with R-ADMIN role."""
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="Admin123!",
            documento="11111111",
            first_name="Admin",
            last_name="User",
        )
        self.admin_role = Role.objects.get_or_create(
            code="R-ADMIN",
            defaults={"name": "Administrador", "type": "interno"},
        )[0]
        UserRole.objects.get_or_create(
            user=self.admin_user,
            role=self.admin_role,
        )
        return self.admin_user

    def create_regular_user(self):
        """Create a regular user without admin role."""
        self.regular_user = User.objects.create_user(
            email="regular@test.com",
            password="Regular123!",
            documento="22222222",
            first_name="Regular",
            last_name="User",
        )
        return self.regular_user


class UserListViewTests(AdminViewTestMixin, TestCase):
    """Test cases for UserListView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.create_regular_user()
        self.url = reverse("accounts_admin:user_list")
        self.client = Client()

    def test_list_requires_login(self):
        """Test that list view requires authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_list_accessible_by_admin(self):
        """Test that admin can access user list."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_list_shows_users(self):
        """Test that user list shows all users."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertContains(response, "admin@test.com")
        self.assertContains(response, "regular@test.com")

    def test_list_filter_by_status(self):
        """Test filtering by user status."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url, {"status": "active"})
        self.assertEqual(response.status_code, 200)

    def test_list_search(self):
        """Test search functionality."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url, {"search": "admin"})
        self.assertEqual(response.status_code, 200)


class UserCreateViewTests(AdminViewTestMixin, TestCase):
    """Test cases for UserCreateView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.url = reverse("accounts_admin:user_create")
        self.client = Client()

    def test_create_page_loads(self):
        """Test that create page loads for admin."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_create_user_success(self):
        """Test successful user creation."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.post(
            self.url,
            {
                "email": "newuser@test.com",
                "documento": "99999999",
                "first_name": "New",
                "last_name": "User",
                "telefono": "1234567890",
            },
        )
        # Should redirect to user detail
        self.assertEqual(response.status_code, 302)
        # Check user was created
        self.assertTrue(User.objects.filter(email="newuser@test.com").exists())

    def test_create_user_duplicate_email(self):
        """Test that duplicate email shows error."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.post(
            self.url,
            {
                "email": "admin@test.com",  # Already exists
                "documento": "99999999",
                "first_name": "New",
                "last_name": "User",
            },
        )
        self.assertEqual(response.status_code, 200)
        # Should show error message
        self.assertContains(response, "Ya existe un usuario con este email")


class UserDetailViewTests(AdminViewTestMixin, TestCase):
    """Test cases for UserDetailView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.create_regular_user()
        self.url = reverse("accounts_admin:user_detail", kwargs={"pk": self.regular_user.pk})
        self.client = Client()

    def test_detail_page_loads(self):
        """Test that detail page loads."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "regular@test.com")

    def test_detail_shows_roles(self):
        """Test that detail page shows user roles."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


class UserUpdateViewTests(AdminViewTestMixin, TestCase):
    """Test cases for UserUpdateView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.create_regular_user()
        self.url = reverse("accounts_admin:user_update", kwargs={"pk": self.regular_user.pk})
        self.client = Client()

    def test_update_page_loads(self):
        """Test that update page loads."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_update_user_success(self):
        """Test successful user update."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.post(
            self.url,
            {
                "email": self.regular_user.email,
                "documento": self.regular_user.documento,
                "first_name": "Updated",
                "last_name": "Name",
                "telefono": "9876543210",
            },
        )
        self.assertEqual(response.status_code, 302)
        # Check user was updated
        self.regular_user.refresh_from_db()
        self.assertEqual(self.regular_user.first_name, "Updated")


class UserToggleActiveViewTests(AdminViewTestMixin, TestCase):
    """Test cases for UserToggleActiveView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.create_regular_user()
        self.url = reverse("accounts_admin:user_toggle", kwargs={"pk": self.regular_user.pk})
        self.client = Client()

    def test_toggle_user_active(self):
        """Test toggling user active status."""
        self.client.login(username="admin@test.com", password="Admin123!")
        self.assertTrue(self.regular_user.is_active)

        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)

        self.regular_user.refresh_from_db()
        self.assertFalse(self.regular_user.is_active)

    def test_cannot_deactivate_self(self):
        """Test that admin cannot deactivate themselves."""
        self.client.login(username="admin@test.com", password="Admin123!")
        self_url = reverse("accounts_admin:user_toggle", kwargs={"pk": self.admin_user.pk})

        response = self.client.post(self_url)
        self.assertEqual(response.status_code, 302)
        # Should show error message
        self.assertContains(response, "No puedes desactivar tu propia cuenta")


class RoleListViewTests(AdminViewTestMixin, TestCase):
    """Test cases for RoleListView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.url = reverse("accounts_admin:role_list")
        self.client = Client()

    def test_list_page_loads(self):
        """Test that role list page loads."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R-ADMIN")


class RoleCreateViewTests(AdminViewTestMixin, TestCase):
    """Test cases for RoleCreateView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.url = reverse("accounts_admin:role_create")
        self.client = Client()

    def test_create_page_loads(self):
        """Test that create role page loads."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_create_role_success(self):
        """Test successful role creation."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.post(
            self.url,
            {
                "code": "R-TEST",
                "name": "Rol de Prueba",
                "type": "interno",
                "description": "Rol creado para pruebas",
            },
        )
        self.assertEqual(response.status_code, 302)
        # Check role was created
        self.assertTrue(Role.objects.filter(code="R-TEST").exists())

    def test_create_role_duplicate_code(self):
        """Test that duplicate role code shows error."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.post(
            self.url,
            {
                "code": "R-ADMIN",  # Already exists
                "name": "Another Admin",
                "type": "interno",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ya existe un rol con este código")


class RoleDetailViewTests(AdminViewTestMixin, TestCase):
    """Test cases for RoleDetailView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.role = Role.objects.get(code="R-ADMIN")
        self.url = reverse("accounts_admin:role_detail", kwargs={"pk": self.role.pk})
        self.client = Client()

    def test_detail_page_loads(self):
        """Test that role detail page loads."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R-ADMIN")


class RoleUpdateViewTests(AdminViewTestMixin, TestCase):
    """Test cases for RoleUpdateView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.role = Role.objects.get(code="R-ADMIN")
        self.url = reverse("accounts_admin:role_update", kwargs={"pk": self.role.pk})
        self.client = Client()

    def test_update_page_loads(self):
        """Test that update role page loads."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)


class UserRoleAssignViewTests(AdminViewTestMixin, TestCase):
    """Test cases for UserRoleAssignView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.create_regular_user()
        self.url = reverse("accounts_admin:user_roles", kwargs={"pk": self.regular_user.pk})
        self.client = Client()

    def test_assign_role_page_loads(self):
        """Test that role assignment page loads."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_assign_role_success(self):
        """Test successful role assignment."""
        # Create a role to assign
        test_role = Role.objects.create(
            code="R-TEST",
            name="Rol de Prueba",
            type="interno",
        )

        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.post(self.url, {"role_id": test_role.pk})

        # Should redirect to user detail
        self.assertEqual(response.status_code, 302)

        # Check role was assigned
        self.assertTrue(
            UserRole.objects.filter(user=self.regular_user, role=test_role).exists()
        )


class UserRoleRevokeViewTests(AdminViewTestMixin, TestCase):
    """Test cases for UserRoleRevokeView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.create_regular_user()

        # Assign a role to regular user
        self.test_role = Role.objects.create(
            code="R-TEST-REVOKE",
            name="Rol de Prueba Revoke",
            type="interno",
        )
        UserRole.objects.create(user=self.regular_user, role=self.test_role)

        self.url = reverse(
            "accounts_admin:user_role_revoke",
            kwargs={"pk": self.regular_user.pk, "role_id": self.test_role.pk},
        )
        self.client = Client()

    def test_revoke_role_success(self):
        """Test successful role revocation."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.post(self.url)

        # Should redirect to user detail
        self.assertEqual(response.status_code, 302)

        # Check role was revoked
        self.assertFalse(
            UserRole.objects.filter(user=self.regular_user, role=self.test_role).exists()
        )


class PermissionTests(AdminViewTestMixin, TestCase):
    """Test cases for admin view permissions."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.create_regular_user()
        self.client = Client()

    def test_non_admin_cannot_access_users(self):
        """Test that non-admin cannot access user list."""
        self.client.login(username="regular@test.com", password="Regular123!")
        response = self.client.get(reverse("accounts_admin:user_list"))
        # Should redirect to dashboard
        self.assertRedirects(response, reverse("dashboard"))

    def test_non_admin_cannot_access_roles(self):
        """Test that non-admin cannot access role list."""
        self.client.client.login(username="regular@test.com", password="Regular123!")
        response = self.client.get(reverse("accounts_admin:role_list"))
        self.assertRedirects(response, reverse("dashboard"))

    def test_anonymous_cannot_access_users(self):
        """Test that anonymous users cannot access user list."""
        response = self.client.get(reverse("accounts_admin:user_list"))
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_anonymous_cannot_access_roles(self):
        """Test that anonymous users cannot access role list."""
        response = self.client.get(reverse("accounts_admin:role_list"))
        self.assertEqual(response.status_code, 302)  # Redirect to login


class PermissionMatrixViewTests(AdminViewTestMixin, TestCase):
    """Test cases for PermissionMatrixView."""

    def setUp(self):
        """Set up test data."""
        self.create_admin_user()
        self.create_regular_user()
        # Use direct URL path since namespace is handled in included URL
        self.url = "/accounts/admin/permisos/"
        self.client = Client()

    def test_matrix_requires_login(self):
        """Test that matrix view requires authentication."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login

    def test_matrix_accessible_by_admin(self):
        """Test that admin can access permission matrix."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_matrix_shows_roles(self):
        """Test that matrix shows roles."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "R-ADMIN")

    def test_non_admin_cannot_access_matrix(self):
        """Test that non-admin cannot access permission matrix."""
        self.client.login(username="regular@test.com", password="Regular123!")
        response = self.client.get(self.url)
        # Should redirect to dashboard
        self.assertRedirects(response, reverse("dashboard"))
