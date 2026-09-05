"""Tests for applications views."""
import uuid
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.applications.models import Solicitud, RequisitoValidacion
from apps.convocatories.models import Convocatory

User = get_user_model()


class ApplicationListViewTest(TestCase):
    """Test ApplicationListView."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="test@example.com",
            documento="12345678",
            first_name="Test",
            last_name="User",
            password="testpass123"
        )
        self.client.force_login(self.user)
    
    def test_list_view_requires_login(self):
        """Test that list view requires login."""
        self.client.logout()
        response = self.client.get(reverse("applications:list"))
        self.assertEqual(response.status_code, 302)  # Redirect to login


class RequisitoValidacionModelTest(TestCase):
    """Test RequisitoValidacion model."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            email="test@example.com",
            documento="12345678",
            first_name="Test",
            last_name="User",
            password="testpass123"
        )
        self.convocatoria = Convocatory.objects.create(
            nombre="Test Convocatoria",
            estado=Convocatory.Estado.EN_INSCRIPCION,
        )
        self.solicitud = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user,
            estado=Solicitud.Estado.RADICADA,
        )
    
    def test_create_validacion(self):
        """Test creating a validacion."""
        validacion = RequisitoValidacion.objects.create(
            solicitud=self.solicitud,
            requisito_code="r1",
            requisito_nombre="Verificar SNIES",
            estado=RequisitoValidacion.Estado.PENDIENTE,
        )
        self.assertEqual(validacion.requisito_code, "r1")
        self.assertEqual(validacion.estado, RequisitoValidacion.Estado.PENDIENTE)
    
    def test_unique_constraint(self):
        """Test unique constraint on solicitud + requisito_code."""
        RequisitoValidacion.objects.create(
            solicitud=self.solicitud,
            requisito_code="r1",
            requisito_nombre="Test",
        )
        with self.assertRaises(Exception):
            RequisitoValidacion.objects.create(
                solicitud=self.solicitud,
                requisito_code="r1",
                requisito_nombre="Test 2",
            )


class RequirementReviewViewTest(TestCase):
    """Test requirement review views."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="revisor@example.com",
            documento="87654321",
            first_name="Revisor",
            last_name="Test",
            password="testpass123"
        )
        # Add R-REVISOR role using custom user_roles
        from apps.accounts.models import Role, UserRole
        self.role = Role.objects.get_or_create(
            code="R-REVISOR",
            defaults={"name": "Revisor", "type": "interno"},
        )[0]
        UserRole.objects.get_or_create(user=self.user, role=self.role)

        self.convocatoria = Convocatory.objects.create(
            nombre="Test Convocatoria",
            estado=Convocatory.Estado.EN_INSCRIPCION,
        )
        self.solicitud = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user,
            estado=Solicitud.Estado.RADICADA,
        )
    
    def test_review_list_requires_revisor_role(self):
        """Test that review list requires R-REVISOR role."""
        self.client.force_login(self.user)
        response = self.client.get(reverse("applications:review_list"))
        # Should work with R-REVISOR role
        self.assertEqual(response.status_code, 200)


class CHG202SpecScenarioTest(TestCase):
    """Tests for CHG-202 spec scenarios: UUID, wizard, upload, submit."""

    def setUp(self):
        """Set up test data."""
        self.client = Client()
        self.user = User.objects.create_user(
            email="aspirante@example.com",
            documento="12345678",
            first_name="Aspirante",
            last_name="Test",
            password="testpass123"
        )
        self.other_user = User.objects.create_user(
            email="otro@example.com",
            documento="87654321",
            first_name="Otro",
            last_name="User",
            password="testpass123"
        )
        self.convocatoria = Convocatory.objects.create(
            nombre="Test Convocatoria 2026",
            codigo="test-2026",
            periodo="2026-1",
            estado=Convocatory.Estado.EN_INSCRIPCION,
        )

    def test_scenario_1_uuid_auto_generation(self):
        """Scenario 1: Creating Solicitud automatically generates UUID."""
        solicitud = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user,
            estado=Solicitud.Estado.BORRADOR,
        )
        # UUID should be auto-generated
        self.assertIsNotNone(solicitud.uuid)
        self.assertIsInstance(solicitud.uuid, uuid.UUID)

    def test_scenario_2_uuid_lookup(self):
        """Scenario 2: Detail view works with UUID."""
        solicitud = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user,
            estado=Solicitud.Estado.RADICADA,
            radicado="RAD-2026-00001",
        )
        # Should be accessible via UUID
        url = reverse("applications:detail", kwargs={"pk": str(solicitud.uuid)})
        self.client.force_login(self.user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RAD-2026-00001")

    def test_scenario_3_list_content(self):
        """Scenario 3: List shows user's applications."""
        # Create applications for our user
        Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user,
            estado=Solicitud.Estado.RADICADA,
            radicado="RAD-2026-00001",
        )
        # Create application for other user
        Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.other_user,
            estado=Solicitud.Estado.RADICADA,
            radicado="RAD-2026-00002",
        )
        self.client.force_login(self.user)
        response = self.client.get(reverse("applications:list"))
        self.assertEqual(response.status_code, 200)
        # Should show our application
        self.assertContains(response, "RAD-2026-00001")
        # Should NOT show other user's application
        self.assertNotContains(response, "RAD-2026-00002")

    def test_scenario_4_detail_ownership(self):
        """Scenario 4: Users cannot view other users' applications (404)."""
        solicitud = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.other_user,
            estado=Solicitud.Estado.RADICADA,
            radicado="RAD-2026-00002",
        )
        # Login as different user
        self.client.force_login(self.user)
        url = reverse("applications:detail", kwargs={"pk": str(solicitud.uuid)})
        response = self.client.get(url)
        # Should return 404
        self.assertEqual(response.status_code, 404)

    def test_scenario_5_draft_save(self):
        """Scenario 5: Wizard saves draft."""
        # Create initial solicitud
        solicitud = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user,
            estado=Solicitud.Estado.BORRADOR,
            current_step=1,
        )
        self.client.force_login(self.user)
        url = reverse("applications:wizard_step", kwargs={"pk": str(solicitud.uuid), "step": 2})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_scenario_6_upload(self):
        """Scenario 6: File upload endpoint exists."""
        solicitud = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user,
            estado=Solicitud.Estado.BORRADOR,
            current_step=4,
        )
        self.client.force_login(self.user)
        url = reverse("applications:upload", kwargs={"pk": str(solicitud.uuid)})
        # Upload view only accepts POST (AJAX), verify URL is routable
        response = self.client.post(url, {"file": ""})
        # Should return 400 (no file) not 404 (missing URL)
        self.assertEqual(response.status_code, 400)

    def test_scenario_7_submit_and_radicado(self):
        """Scenario 7: Submit creates radicado and updates status."""
        from apps.applications.services.wizard_service import submit, WizardError

        solicitud = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user,
            estado=Solicitud.Estado.BORRADOR,
            current_step=5,
            # Required data for submit
            datos_personales={"nombre": "Test", "apellido": "User"},
            datos_academicos={"programa": "Ingeniería"},
        )
        # Submit the application
        submit(solicitud, consentimiento=True, actor=self.user)

        # Refresh from DB
        solicitud.refresh_from_db()

        # Should have radicado and be in RADICADA or COMPLETA state
        self.assertIsNotNone(solicitud.radicado)
        self.assertTrue(
            solicitud.estado in [Solicitud.Estado.RADICADA, Solicitud.Estado.COMPLETA],
            f"Expected RADICADA or COMPLETA, got {solicitud.estado}"
        )
