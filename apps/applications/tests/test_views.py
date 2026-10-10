"""Tests for applications views."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from apps.applications.models import RequisitoValidacion, Solicitud
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
            password="testpass123",
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
            password="testpass123",
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
            password="testpass123",
        )
        # Assign R-REVISOR through the CHG-112 role system
        # (permission mixin checks user.user_roles, not auth.Group).
        from apps.accounts.models import Role
        from apps.accounts.services.assignment import assign_role_to_user
        from apps.accounts.services.sync import sync_role_to_group

        self.role = Role.objects.create(
            code="R-REVISOR",
            name="Revisor",
            type="interno",
            description="Revisor de requisitos (synthetic test role).",
        )
        sync_role_to_group(self.role)
        assign_role_to_user(self.user, self.role)

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
