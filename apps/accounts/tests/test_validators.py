"""Tests for accounts validators."""
from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.accounts.validators import FodejasPasswordValidator


class FodejasPasswordValidatorTests(TestCase):
    """Test the FodejasPasswordValidator."""

    def setUp(self):
        """Set up the validator."""
        self.validator = FodejasPasswordValidator(min_length=8)

    def test_valid_password(self):
        """Test that a valid password passes validation."""
        password = "Abcdef1!"
        try:
            self.validator.validate(password)
        except ValidationError:
            self.fail("Valid password raised ValidationError")

    def test_password_too_short(self):
        """Test that passwords shorter than 8 characters fail."""
        password = "Abc1!"
        with self.assertRaises(ValidationError) as context:
            self.validator.validate(password)
        self.assertIn("al menos 8 caracteres", str(context.exception))

    def test_password_without_uppercase(self):
        """Test that passwords without uppercase fail."""
        password = "abcdef1!"
        with self.assertRaises(ValidationError) as context:
            self.validator.validate(password)
        self.assertIn("letra mayúscula", str(context.exception))

    def test_password_without_digit(self):
        """Test that passwords without digits fail."""
        password = "Abcdefg!"
        with self.assertRaises(ValidationError) as context:
            self.validator.validate(password)
        self.assertIn("número", str(context.exception))

    def test_password_without_symbol(self):
        """Test that passwords without symbols fail."""
        password = "Abcdef12"
        with self.assertRaises(ValidationError) as context:
            self.validator.validate(password)
        self.assertIn("símbolo", str(context.exception))

    def test_password_with_all_requirements(self):
        """Test password with all requirements met."""
        passwords = [
            "Password1!",
            "Test1234$",
            "Secure@123",
            "MyP@ssw0rd",
        ]
        for password in passwords:
            try:
                self.validator.validate(password)
            except ValidationError:
                self.fail(f"Password {password} should be valid")

    def test_get_help_text(self):
        """Test that help text is returned."""
        help_text = self.validator.get_help_text()
        self.assertIn("8 caracteres", help_text)
        self.assertIn("mayúscula", help_text)
        self.assertIn("número", help_text)
        self.assertIn("símbolo", help_text)

    def test_custom_min_length(self):
        """Test validator with custom minimum length."""
        validator = FodejasPasswordValidator(min_length=10)
        password = "Abcdef1!"  # 8 chars - should fail with min_length=10
        with self.assertRaises(ValidationError):
            validator.validate(password)

    def test_password_with_spaces(self):
        """Test password containing spaces (allowed but not typical)."""
        # Spaces are allowed as they're not in the excluded characters
        password = "Abc 123!"
        try:
            self.validator.validate(password)
        except ValidationError:
            self.fail("Password with spaces should be valid")
