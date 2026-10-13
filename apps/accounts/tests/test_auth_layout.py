"""Tests for auth page layout: sidebar/chrome must be absent on login/register/password pages.

CAP-001 (Auth/Roles) — sidebar is UI chrome, not auth logic.
Validates user feedback: /accounts/login/ must not show the sidebar.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AuthLayoutTests(TestCase):
    """Sidebar and nav chrome MUST be absent on all auth pages."""

    # ── Auth pages: sidebar must be HIDDEN ────────────────────────────────

    def test_login_page_no_sidebar(self):
        """Anonymous GET /accounts/login/ → 200, no #sidebar, no mobile-topbar, no #mobileSidebar."""
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn('id="sidebar"', html)
        self.assertNotIn('class="mobile-topbar"', html)
        self.assertNotIn('id="mobileSidebar"', html)

    def test_register_page_no_sidebar(self):
        """Anonymous GET /accounts/register/ → 200, no #sidebar, no mobile-topbar, no #mobileSidebar."""
        response = self.client.get(reverse("accounts:register"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn('id="sidebar"', html)
        self.assertNotIn('class="mobile-topbar"', html)
        self.assertNotIn('id="mobileSidebar"', html)

    def test_password_reset_page_no_sidebar(self):
        """Anonymous GET /accounts/password-reset/ → 200, no #sidebar, no mobile-topbar, no #mobileSidebar."""
        response = self.client.get(reverse("accounts:password_reset"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn('id="sidebar"', html)
        self.assertNotIn('class="mobile-topbar"', html)
        self.assertNotIn('id="mobileSidebar"', html)

    # ── Authenticated pages: sidebar must be PRESENT ──────────────────────

    def test_dashboard_has_sidebar(self):
        """Authenticated GET /accounts/dashboard/ → 200, #sidebar IS present."""
        user = User.objects.create_user(
            email="sidebar-auth@test.com",
            password="Testpass123!",
            documento="11111111",
            first_name="Sidebar",
            last_name="Auth",
        )
        self.client.login(username="sidebar-auth@test.com", password="Testpass123!")
        response = self.client.get(reverse("accounts:dashboard"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn('id="sidebar"', html)

    # ── Public portal: sidebar must stay ──────────────────────────────────

    def test_transparencia_index_has_sidebar(self):
        """Anonymous GET /transparencia/ → 200, #sidebar IS present (public portal keeps chrome)."""
        response = self.client.get("/transparencia/")
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertIn('id="sidebar"', html)
