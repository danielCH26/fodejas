"""Tests for audit HTML views."""
import uuid
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import Role, UserRole
from apps.audit.models import AuditEvent
from apps.audit import selectors

User = get_user_model()


class AuditPermissionTests(TestCase):
    """Test audit view permissions."""

    def setUp(self):
        """Set up test users with different roles."""
        # Create roles
        self.role_admin, _ = Role.objects.get_or_create(
            code="R-ADMIN",
            defaults={"name": "Administrador", "type": "interno"},
        )
        self.role_control, _ = Role.objects.get_or_create(
            code="R-CONTROL",
            defaults={"name": "Control", "type": "interno"},
        )
        self.role_aspirante, _ = Role.objects.get_or_create(
            code="R-ASPIRANTE",
            defaults={"name": "Aspirante", "type": "externo"},
        )

        # Create users
        self.admin_user = User.objects.create_user(
            email="admin@test.com",
            password="Admin123!",
            documento="11111111",
            first_name="Admin",
            last_name="User",
        )
        UserRole.objects.create(user=self.admin_user, role=self.role_admin)

        self.control_user = User.objects.create_user(
            email="control@test.com",
            password="Control123!",
            documento="22222222",
            first_name="Control",
            last_name="User",
        )
        UserRole.objects.create(user=self.control_user, role=self.role_control)

        self.aspirante_user = User.objects.create_user(
            email="aspirante@test.com",
            password="Aspirante123!",
            documento="33333333",
            first_name="Aspirante",
            last_name="User",
        )
        UserRole.objects.create(user=self.aspirante_user, role=self.role_aspirante)

        self.dashboard_url = reverse("audit_dashboard")
        self.verify_url = reverse("audit_verify")

    def test_r_admin_has_access_to_audit_dashboard(self):
        """Test that R-ADMIN has access to audit dashboard."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_r_control_has_access_to_audit_dashboard(self):
        """Test that R-CONTROL has access to audit dashboard."""
        self.client.login(username="control@test.com", password="Control123!")
        response = self.client.get(self.dashboard_url)
        self.assertEqual(response.status_code, 200)

    def test_r_aspirante_denied_access_to_audit_dashboard(self):
        """Test that R-ASPIRANTE is denied access to audit dashboard."""
        self.client.login(username="aspirante@test.com", password="Aspirante123!")
        response = self.client.get(self.dashboard_url)
        # Should redirect or show error
        self.assertIn(response.status_code, [302, 403])

    def test_unauthenticated_user_redirected_from_audit(self):
        """Test that unauthenticated users are redirected."""
        response = self.client.get(self.dashboard_url)
        self.assertRedirects(response, f"/accounts/login/?next={self.dashboard_url}")

    def test_r_admin_has_access_to_verify(self):
        """Test that R-ADMIN has access to verify page."""
        self.client.login(username="admin@test.com", password="Admin123!")
        response = self.client.get(self.verify_url)
        self.assertEqual(response.status_code, 200)

    def test_r_control_denied_access_to_verify(self):
        """Test that R-CONTROL is denied access to verify page."""
        self.client.login(username="control@test.com", password="Control123!")
        response = self.client.get(self.verify_url)
        # Should redirect or show error - only R-ADMIN can verify
        self.assertIn(response.status_code, [302, 403])


class AuditDashboardViewTests(TestCase):
    """Test audit dashboard view functionality."""

    def setUp(self):
        """Set up test data."""
        self.role_admin, _ = Role.objects.get_or_create(
            code="R-ADMIN",
            defaults={"name": "Administrador", "type": "interno"},
        )
        self.user = User.objects.create_user(
            email="audit@test.com",
            password="Audit123!",
            documento="44444444",
            first_name="Audit",
            last_name="User",
        )
        UserRole.objects.create(user=self.user, role=self.role_admin)

        # Create some audit events
        self.event1 = AuditEvent.objects.create(
            actor=self.user,
            action="CREATE",
            entity="Convocatoria",
            entity_id=uuid.uuid4(),
            changes={"before": None, "after": {"name": "Test"}},
            module="convocatories",
            previous_hash="0" * 64,
            current_hash="a" * 64,
        )
        self.event2 = AuditEvent.objects.create(
            actor=self.user,
            action="UPDATE",
            entity="Convocatoria",
            entity_id=uuid.uuid4(),
            changes={"before": {"name": "Old"}, "after": {"name": "New"}},
            module="convocatories",
            previous_hash="a" * 64,
            current_hash="b" * 64,
        )

    def test_dashboard_loads(self):
        """Test that dashboard loads successfully."""
        self.client.login(username="audit@test.com", password="Audit123!")
        response = self.client.get(reverse("audit_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "audit/index.html")

    def test_dashboard_shows_events(self):
        """Test that dashboard shows audit events."""
        self.client.login(username="audit@test.com", password="Audit123!")
        response = self.client.get(reverse("audit_dashboard"))
        self.assertContains(response, "CREATE")
        self.assertContains(response, "UPDATE")

    def test_dashboard_filters_by_action(self):
        """Test that filtering by action works."""
        self.client.login(username="audit@test.com", password="Audit123!")
        url = f"{reverse('audit_dashboard')}?action=CREATE"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # Should only show CREATE events
        self.assertContains(response, "CREATE")

    def test_dashboard_filters_by_entity(self):
        """Test that filtering by entity works."""
        self.client.login(username="audit@test.com", password="Audit123!")
        url = f"{reverse('audit_dashboard')}?entity=Convocatoria"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Convocatoria")

    def test_dashboard_shows_stats(self):
        """Test that dashboard shows statistics."""
        self.client.login(username="audit@test.com", password="Audit123!")
        response = self.client.get(reverse("audit_dashboard"))
        self.assertEqual(response.status_code, 200)
        # Check that total count is shown
        self.assertContains(response, "2")


class AuditDetailViewTests(TestCase):
    """Test audit event detail view."""

    def setUp(self):
        """Set up test data."""
        self.role_admin, _ = Role.objects.get_or_create(
            code="R-ADMIN",
            defaults={"name": "Administrador", "type": "interno"},
        )
        self.user = User.objects.create_user(
            email="auditdetail@test.com",
            password="AuditDetail123!",
            documento="55555555",
            first_name="AuditDetail",
            last_name="User",
        )
        UserRole.objects.create(user=self.user, role=self.role_admin)

        # Create an audit event
        self.event = AuditEvent.objects.create(
            actor=self.user,
            action="UPDATE",
            entity="Convocatoria",
            entity_id=uuid.uuid4(),
            changes={
                "before": {"name": "Old Name", "status": "draft"},
                "after": {"name": "New Name", "status": "published"},
            },
            module="convocatories",
            previous_hash="0" * 64,
            current_hash="c" * 64,
        )

    def test_detail_view_loads(self):
        """Test that detail view loads successfully."""
        self.client.login(username="auditdetail@test.com", password="AuditDetail123!")
        url = reverse("audit_detail", kwargs={"id": self.event.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "audit/detail.html")

    def test_detail_view_shows_changes(self):
        """Test that detail view shows changes."""
        self.client.login(username="auditdetail@test.com", password="AuditDetail123!")
        url = reverse("audit_detail", kwargs={"id": self.event.id})
        response = self.client.get(url)
        self.assertContains(response, "Old Name")
        self.assertContains(response, "New Name")

    def test_detail_view_404_for_nonexistent_event(self):
        """Test that detail view returns 404 for nonexistent event."""
        self.client.login(username="auditdetail@test.com", password="AuditDetail123!")
        url = reverse("audit_detail", kwargs={"id": uuid.uuid4()})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class AuditChainVerifyTests(TestCase):
    """Test audit chain verification."""

    def setUp(self):
        """Set up test data."""
        self.role_admin, _ = Role.objects.get_or_create(
            code="R-ADMIN",
            defaults={"name": "Administrador", "type": "interno"},
        )
        self.user = User.objects.create_user(
            email="auditverify@test.com",
            password="AuditVerify123!",
            documento="66666666",
            first_name="AuditVerify",
            last_name="User",
        )
        UserRole.objects.create(user=self.user, role=self.role_admin)

    def test_verify_view_loads(self):
        """Test that verify view loads successfully."""
        self.client.login(username="auditverify@test.com", password="AuditVerify123!")
        response = self.client.get(reverse("audit_verify"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "audit/verify.html")

    def test_verify_chain_returns_valid_for_empty(self):
        """Test that verify_chain returns valid for empty chain."""
        # Clear all events
        AuditEvent.objects.all().delete()
        result = selectors.verify_audit_chain()
        self.assertTrue(result["is_valid"])

    def test_verify_chain_returns_valid_for_valid_chain(self):
        """Test that verify_chain returns valid for valid chain."""
        # Create a valid chain
        event = AuditEvent.objects.create(
            actor=self.user,
            action="CREATE",
            entity="Test",
            entity_id=uuid.uuid4(),
            module="test",
            previous_hash="0" * 64,
            current_hash="abc123",
        )
        result = selectors.verify_audit_chain()
        self.assertTrue(result["is_valid"])


class AuditSelectorsTests(TestCase):
    """Test audit selector functions."""

    def setUp(self):
        """Set up test data."""
        self.role_admin, _ = Role.objects.get_or_create(
            code="R-ADMIN",
            defaults={"name": "Administrador", "type": "interno"},
        )
        self.user = User.objects.create_user(
            email="auditselectors@test.com",
            password="AuditSelectors123!",
            documento="77777777",
            first_name="AuditSelectors",
            last_name="User",
        )
        UserRole.objects.create(user=self.user, role=self.role_admin)

    def test_get_audit_events_filters_by_actor(self):
        """Test get_audit_events filters by actor."""
        event = AuditEvent.objects.create(
            actor=self.user,
            action="CREATE",
            entity="Test",
            entity_id=uuid.uuid4(),
            module="test",
            previous_hash="0" * 64,
            current_hash="def456",
        )
        events = selectors.get_audit_events(actor=self.user.id)
        self.assertEqual(events.count(), 1)
        self.assertEqual(events.first(), event)

    def test_get_audit_events_filters_by_action(self):
        """Test get_audit_events filters by action."""
        AuditEvent.objects.create(
            actor=self.user,
            action="CREATE",
            entity="Test",
            entity_id=uuid.uuid4(),
            module="test",
            previous_hash="0" * 64,
            current_hash="ghi789",
        )
        events = selectors.get_audit_events(action="UPDATE")
        self.assertEqual(events.count(), 0)

    def test_get_audit_events_filters_by_entity(self):
        """Test get_audit_events filters by entity."""
        AuditEvent.objects.create(
            actor=self.user,
            action="CREATE",
            entity="Convocatoria",
            entity_id=uuid.uuid4(),
            module="convocatories",
            previous_hash="0" * 64,
            current_hash="jkl012",
        )
        events = selectors.get_audit_events(entity="Convocatoria")
        self.assertEqual(events.count(), 1)

    def test_get_audit_event_by_id_returns_event(self):
        """Test get_audit_event_by_id returns event."""
        event = AuditEvent.objects.create(
            actor=self.user,
            action="CREATE",
            entity="Test",
            entity_id=uuid.uuid4(),
            module="test",
            previous_hash="0" * 64,
            current_hash="mno345",
        )
        result = selectors.get_audit_event_by_id(str(event.id))
        self.assertEqual(result, event)

    def test_get_audit_event_by_id_returns_none_for_invalid(self):
        """Test get_audit_event_by_id returns None for invalid ID."""
        result = selectors.get_audit_event_by_id(str(uuid.uuid4()))
        self.assertIsNone(result)
