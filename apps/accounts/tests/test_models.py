"""Tests for accounts models."""
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