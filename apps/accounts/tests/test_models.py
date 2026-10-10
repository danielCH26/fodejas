"""Tests for accounts models."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from apps.accounts.models import Role


class CustomUserModelTests(TestCase):
    """Test the CustomUser model."""

    def test_user_model_is_custom_user(self):
        """Test that AUTH_USER_MODEL is set to accounts.CustomUser."""
        # This test will fail initially because AUTH_USER_MODEL is not set
        User = get_user_model()
        self.assertEqual(User.__name__, "CustomUser")

    def test_user_creation_with_required_fields(self):
        """Test creating a user with required fields."""
        User = get_user_model()
        user = User.objects.create_user(
            email="test@example.com",
            password="Test123!@#",
            documento="12345678",
            first_name="Test",
            last_name="User",
        )
        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("Test123!@#"))
        self.assertEqual(user.documento, "12345678")
        self.assertEqual(user.first_name, "Test")
        self.assertEqual(user.last_name, "User")
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_email_is_username_field(self):
        """Test that email is the USERNAME_FIELD."""
        User = get_user_model()
        self.assertEqual(User.USERNAME_FIELD, "email")

    def test_required_fields_includes_documento_and_names(self):
        """Test that documento, first_name, and last_name are in REQUIRED_FIELDS."""
        User = get_user_model()
        self.assertIn("documento", User.REQUIRED_FIELDS)
        self.assertIn("first_name", User.REQUIRED_FIELDS)
        self.assertIn("last_name", User.REQUIRED_FIELDS)

    def test_email_must_be_unique(self):
        """Test that email field is unique."""
        User = get_user_model()
        User.objects.create_user(
            email="duplicate@example.com",
            password="Test123!@#",
            documento="11111111",
            first_name="First",
            last_name="User",
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="duplicate@example.com",
                password="Test123!@#",
                documento="22222222",
                first_name="Second",
                last_name="User",
            )

    def test_documento_must_be_unique(self):
        """Test that documento field is unique."""
        User = get_user_model()
        User.objects.create_user(
            email="first@example.com",
            password="Test123!@#",
            documento="12345678",
            first_name="First",
            last_name="User",
        )
        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="second@example.com",
                password="Test123!@#",
                documento="12345678",
                first_name="Second",
                last_name="User",
            )


class RoleModelTests(TestCase):
    """Test the Role model."""

    def test_role_creation(self):
        """Test creating a role with required fields."""
        role = Role.objects.create(
            code="R-TEST-ROLE",
            name="Test Role",
            type="externo",
        )
        self.assertEqual(role.code, "R-TEST-ROLE")
        self.assertEqual(role.name, "Test Role")
        self.assertEqual(role.type, "externo")

    def test_role_code_must_be_unique(self):
        """Test that role code field is unique."""
        Role.objects.create(
            code="R-TEST-UNIQUE",
            name="Test Unique",
            type="externo",
        )
        with self.assertRaises(IntegrityError):
            Role.objects.create(
                code="R-TEST-UNIQUE",
                name="Another Test",
                type="externo",
            )

    def test_role_type_constraint(self):
        """Test that role type must be either 'interno' or 'externo'."""
        # This should work
        role = Role.objects.create(
            code="R-TEST",
            name="Test Role",
            type="interno",
        )
        self.assertEqual(role.type, "interno")

        # Creating with invalid type should raise an error
        # Note: This test might pass/fail depending on how Django handles CheckConstraint
        with self.assertRaises(Exception):
            Role.objects.create(
                code="R-INVALID",
                name="Invalid Role",
                type="invalid",
            )

    def test_role_has_group_foreign_key(self):
        """Test that Role model has a ForeignKey to auth.Group."""
        # Import at function level to avoid circular imports
        from django.contrib.auth.models import Group

        from apps.accounts.models import Role

        # Create a test group
        group = Group.objects.create(name="Test Group")

        # Create role with group reference
        role = Role.objects.create(
            code="R-WITH-GROUP",
            name="Role With Group",
            type="interno",
            group=group,
        )

        # Test the relationship
        self.assertEqual(role.group, group)
        self.assertEqual(role.group.name, "Test Group")

        # Test reverse relationship if it exists
        # This would test if group.role exists (OneToOne reverse)
        try:
            # Check if group.role exists (OneToOne reverse)
            if hasattr(group, "role"):
                self.assertEqual(group.role, role)
        except AttributeError:
            # It might not be a OneToOne, could be ForeignKey
            pass

    def test_role_can_exist_without_group(self):
        """Test that Role can be created without a group (field is nullable)."""
        from apps.accounts.models import Role

        # Create role without group
        role = Role.objects.create(
            code="R-NO-GROUP",
            name="Role Without Group",
            type="externo",
            # group is not provided, should be None
        )

        # Test that group is None
        self.assertIsNone(role.group)

        # Test that role still has all other fields
        self.assertEqual(role.code, "R-NO-GROUP")
        self.assertEqual(role.name, "Role Without Group")
        self.assertEqual(role.type, "externo")


class PermissionModelTests(TestCase):
    """Test the Permission model."""

    def test_permission_creation(self):
        """Test creating a permission with required fields."""
        from apps.accounts.models import Permission

        permission = Permission.objects.create(
            app_label="applications",
            action="add_application",
        )
        self.assertEqual(permission.app_label, "applications")
        self.assertEqual(permission.action, "add_application")
        self.assertIsNone(permission.convocation_scope_id)
        self.assertIsNone(permission.stage)

    def test_permission_has_auth_permission_foreign_key(self):
        """Test that Permission model has a ForeignKey to auth.Permission."""
        # Import at function level to avoid circular imports
        from django.contrib.auth.models import Permission as AuthPermission

        # Create an auth permission
        from django.contrib.contenttypes.models import ContentType

        from apps.accounts.models import Permission

        content_type = ContentType.objects.create(app_label="accounts", model="test")
        auth_perm = AuthPermission.objects.create(
            codename="test_permission",
            name="Test Permission",
            content_type=content_type,
        )

        # Create permission with auth_permission reference
        permission = Permission.objects.create(
            app_label="applications",
            action="view_convocatory",
            auth_permission=auth_perm,
        )

        # Test the relationship
        self.assertEqual(permission.auth_permission, auth_perm)
        self.assertEqual(permission.auth_permission.codename, "test_permission")

        # Test reverse relationship if it exists
        try:
            # Check if auth_perm.custom_permission exists (OneToOne reverse)
            if hasattr(auth_perm, "custom_permission"):
                self.assertEqual(auth_perm.custom_permission, permission)
        except AttributeError:
            # It might not be a OneToOne, could be ForeignKey
            pass

    def test_permission_can_exist_without_auth_permission(self):
        """Test that Permission can be created without auth_permission (field is nullable)."""
        from apps.accounts.models import Permission

        # Create permission without auth_permission
        permission = Permission.objects.create(
            app_label="convocatories",
            action="edit_convocatory",
            # auth_permission is not provided, should be None
        )

        # Test that auth_permission is None
        self.assertIsNone(permission.auth_permission)

        # Test that permission still has all other fields
        self.assertEqual(permission.app_label, "convocatories")
        self.assertEqual(permission.action, "edit_convocatory")


@pytest.mark.django_db
class TestConsentimiento:
    """Test Consentimiento model for habeas data."""

    def test_consentimiento_creation(self):
        """Test creating a consentimiento record."""
        import hashlib

        from django.contrib.auth import get_user_model

        from apps.accounts.models import Consentimiento

        User = get_user_model()
        user = User.objects.create_user(
            email="consent@test.com",
            password="Test123!",
            documento="12345678",
        )

        texto = "Texto de política de privacidad"
        hash_texto = hashlib.sha256(texto.encode()).hexdigest()

        consentimiento = Consentimiento.objects.create(
            titular=user,
            tipo="tratamiento_datos",
            version_texto=texto,
            version_etiqueta="v1",
            hash_texto=hash_texto,
            ip="127.0.0.1",
        )

        assert consentimiento.titular == user
        assert consentimiento.tipo == "tratamiento_datos"


@pytest.mark.django_db
class TestSolicitudHabeasData:
    """Test SolicitudHabeasData model."""

    def test_solicitud_creation(self):
        """Test creating a habeas data request."""
        from django.contrib.auth import get_user_model
        from django.utils import timezone

        from apps.accounts.models import SolicitudHabeasData

        User = get_user_model()
        user = User.objects.create_user(
            email="hd@test.com",
            password="Test123!",
            documento="11223344",
        )

        fecha_limite = timezone.now() + timezone.timedelta(days=30)

        solicitud = SolicitudHabeasData.objects.create(
            titular=user,
            tipo="consulta",
            descripcion="Quiero ejercer mi derecho de consulta",
            fecha_limite=fecha_limite,
        )

        assert solicitud.titular == user
        assert solicitud.tipo == "consulta"
        assert solicitud.estado == "radicada"
