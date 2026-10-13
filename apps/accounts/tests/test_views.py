"""Integration tests for accounts views."""

import uuid

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Notification, Role, UserRole
from apps.audit.services import log_audit_event

User = get_user_model()


class LoginViewTests(TestCase):
    """Test login view."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            email="login@test.com",
            password="Login123!",
            documento="11111111",
            first_name="Login",
            last_name="Test",
        )
        self.url = reverse("accounts:login")

    def test_login_page_loads(self):
        """Test that login page loads successfully."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/login.html")

    def test_login_success_redirects_to_dashboard(self):
        """Test that successful login redirects to dashboard."""
        response = self.client.post(
            self.url,
            {"username": "login@test.com", "password": "Login123!"},
        )
        self.assertRedirects(response, reverse("accounts:dashboard"))

    def test_login_failure_shows_error(self):
        """Test that login failure shows error message."""
        response = self.client.post(
            self.url,
            {"username": "login@test.com", "password": "wrongpassword"},
        )
        self.assertEqual(response.status_code, 200)
        # Django shows "alert alert-danger" for errors
        self.assertContains(response, "alert")

    def test_authenticated_user_redirected_from_login(self):
        """Test that authenticated user is redirected from login page."""
        self.client.login(username="login@test.com", password="Login123!")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("accounts:dashboard"))


class RegisterViewTests(TestCase):
    """Test registration view."""

    def setUp(self):
        """Set up test data."""
        # Create R-ASPIRANTE role for registration tests
        Role.objects.get_or_create(
            code="R-ASPIRANTE",
            defaults={"name": "Aspirante", "type": "externo"},
        )
        self.url = reverse("accounts:register")

    def test_register_page_loads(self):
        """Test that register page loads successfully."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/register.html")

    def test_register_success_creates_user(self):
        """Test that successful registration creates a user."""
        self.client.post(
            self.url,
            {
                "email": "new@example.com",
                "documento": "99999999",
                "first_name": "New",
                "last_name": "User",
                "password1": "Newuser123!",
                "password2": "Newuser123!",
            },
        )
        self.assertTrue(User.objects.filter(email="new@example.com").exists())

    def test_register_success_assigns_aspirante_role(self):
        """Test that new user gets R-ASPIRANTE role."""
        response = self.client.post(
            self.url,
            {
                "email": "aspirante@example.com",
                "documento": "88888888",
                "first_name": "John",
                "last_name": "Doe",
                "password1": "NewUser123!",
                "password2": "NewUser123!",
            },
        )
        # Should redirect to login after successful registration
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email="aspirante@example.com")
        user_roles = UserRole.objects.filter(user=user)
        self.assertTrue(user_roles.exists())
        self.assertEqual(user_roles.first().role.code, "R-ASPIRANTE")

    def test_register_duplicate_email_fails(self):
        """Test that duplicate email shows error."""
        User.objects.create_user(
            email="duplicate@example.com",
            password="Test123!",
            documento="77777777",
            first_name="Duplicate",
            last_name="Test",
        )
        response = self.client.post(
            self.url,
            {
                "email": "duplicate@example.com",
                "documento": "66666666",
                "first_name": "Another",
                "last_name": "User",
                "password1": "User123!",
                "password2": "User123!",
            },
        )
        self.assertContains(response, "Ya existe una cuenta")

    def test_authenticated_user_redirected_from_register(self):
        """Test that authenticated user is redirected from register."""
        User.objects.create_user(
            email="auth@example.com",
            password="Auth123!",
            documento="55555555",
            first_name="Auth",
            last_name="User",
        )
        self.client.login(username="auth@example.com", password="Auth123!")
        response = self.client.get(self.url)
        self.assertRedirects(response, reverse("accounts:dashboard"))


class DashboardViewTests(TestCase):
    """Test dashboard view."""

    def setUp(self):
        """Set up test user with role."""
        self.user = User.objects.create_user(
            email="dashboard@test.com",
            password="Dash123!",
            documento="44444444",
            first_name="Dashboard",
            last_name="Test",
        )
        # Use get_or_create because roles are seeded
        self.role, _ = Role.objects.get_or_create(
            code="R-COORD",
            defaults={"name": "Coordinador", "type": "interno", "description": ""},
        )
        UserRole.objects.get_or_create(
            user=self.user,
            role=self.role,
            convocation_scope_id=None,
        )
        self.url = reverse("accounts:dashboard")

    def test_dashboard_requires_login(self):
        """Test that dashboard requires authentication."""
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_dashboard_loads_for_authenticated_user(self):
        """Test that dashboard loads for authenticated user."""
        self.client.login(username="dashboard@test.com", password="Dash123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/dashboard.html")

    def test_dashboard_shows_user_info(self):
        """Test that dashboard shows user information."""
        self.client.login(username="dashboard@test.com", password="Dash123!")
        response = self.client.get(self.url)
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "Test")

    def test_dashboard_shows_navigation_for_role(self):
        """Test that dashboard shows role-specific navigation."""
        self.client.login(username="dashboard@test.com", password="Dash123!")
        response = self.client.get(self.url)
        self.assertContains(response, "Convocatorias")
        self.assertContains(response, "Postulaciones")

    def test_dashboard_shows_user_notifications(self):
        """Test that the dashboard renders the user's notifications."""
        Notification.objects.create(
            recipient=self.user,
            event="application.approved",
            tipo="success",
            titulo="Postulación aprobada",
            mensaje="¡Felicidades! Su postulación ha sido aprobada.",
        )
        self.client.login(username="dashboard@test.com", password="Dash123!")
        response = self.client.get(self.url)
        self.assertContains(response, "Postulación aprobada")
        self.assertIn("notifications", response.context)
        self.assertEqual(len(response.context["notifications"]), 1)

    def test_dashboard_excludes_other_users_notifications(self):
        """Test that other users' notifications never leak into the dashboard."""
        other = User.objects.create_user(
            email="other@test.com",
            password="Other123!",
            documento="55555555",
            first_name="Other",
            last_name="User",
        )
        Notification.objects.create(
            recipient=other,
            event="application.rejected",
            tipo="error",
            titulo="Notificación privada",
            mensaje="Solo para other@test.com",
        )
        self.client.login(username="dashboard@test.com", password="Dash123!")
        response = self.client.get(self.url)
        self.assertNotContains(response, "Notificación privada")

    def test_dashboard_shows_unread_count(self):
        """Test that unread notifications are counted in context."""
        Notification.objects.create(
            recipient=self.user,
            event="habeas.resolved",
            tipo="info",
            titulo="Sin leer",
            mensaje="Notificación sin leer",
        )
        self.client.login(username="dashboard@test.com", password="Dash123!")
        response = self.client.get(self.url)
        self.assertEqual(response.context["unread_count"], 1)

    def test_dashboard_shows_recent_activity(self):
        """Test that the dashboard renders the user's recent audit events."""
        log_audit_event(
            actor=self.user,
            action="CREATE",
            entity="Application",
            entity_id=uuid.uuid4(),
            changes={},
            module="accounts",
        )
        self.client.login(username="dashboard@test.com", password="Dash123!")
        response = self.client.get(self.url)
        self.assertIn("recent_events", response.context)
        self.assertEqual(len(response.context["recent_events"]), 1)
        self.assertContains(response, "Application")

    def test_dashboard_excludes_other_users_activity(self):
        """Test that other users' audit events never leak into the dashboard."""
        other = User.objects.create_user(
            email="actor2@test.com",
            password="Actor123!",
            documento="66666666",
            first_name="Other",
            last_name="Actor",
        )
        log_audit_event(
            actor=other,
            action="LOGIN",
            entity="User",
            entity_id=uuid.uuid4(),
            changes={},
            module="accounts",
        )
        self.client.login(username="dashboard@test.com", password="Dash123!")
        response = self.client.get(self.url)
        self.assertEqual(len(response.context["recent_events"]), 0)


class ProfileViewTests(TestCase):
    """Test profile view."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            email="profile@test.com",
            password="Profile123!",
            documento="33333333",
            first_name="Profile",
            last_name="Test",
        )
        self.url = reverse("accounts:profile")

    def test_profile_requires_login(self):
        """Test that profile requires authentication."""
        response = self.client.get(self.url)
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={self.url}")

    def test_profile_loads_for_authenticated_user(self):
        """Test that profile loads for authenticated user."""
        self.client.login(username="profile@test.com", password="Profile123!")
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "accounts/profile.html")

    def test_profile_shows_user_data(self):
        """Test that profile shows user data."""
        self.client.login(username="profile@test.com", password="Profile123!")
        response = self.client.get(self.url)
        self.assertContains(response, "profile@test.com")
        self.assertContains(response, "33333333")


class LogoutViewTests(TestCase):
    """Test logout view."""

    def setUp(self):
        """Set up test user."""
        self.user = User.objects.create_user(
            email="logout@test.com",
            password="Logout123!",
            documento="22222222",
            first_name="Logout",
            last_name="Test",
        )
        self.url = reverse("accounts:logout")

    def test_logout_redirects_to_login(self):
        """Test that logout redirects to login page."""
        self.client.login(username="logout@test.com", password="Logout123!")
        response = self.client.post(self.url)
        self.assertRedirects(response, reverse("accounts:login"))

    def test_logout_clears_session(self):
        """Test that logout clears the session."""
        self.client.login(username="logout@test.com", password="Logout123!")
        self.client.post(self.url)
        # After logout, accessing a protected view should redirect
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertRedirects(
            response, f"{reverse('accounts:login')}?next={reverse('accounts:dashboard')}"
        )
