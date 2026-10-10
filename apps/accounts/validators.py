"""Custom validators for accounts app."""
import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class FodejasPasswordValidator:
    """
    Validate that the password meets FODEJAS requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one digit
    - At least one symbol (special character)
    """

    def __init__(self, min_length=8):
        self.min_length = min_length

    def validate(self, password, user=None):
        """Validate password against FODEJAS requirements."""
        errors = []

        # Check minimum length
        if len(password) < self.min_length:
            errors.append(
                _(
                    "La contraseña debe tener al menos %(min_length)d caracteres."
                ) % {"min_length": self.min_length}
            )

        # Check for at least one uppercase letter
        if not re.search(r"[A-Z]", password):
            errors.append(
                _("La contraseña debe contener al menos una letra mayúscula.")
            )

        # Check for at least one digit
        if not re.search(r"\d", password):
            errors.append(
                _("La contraseña debe contener al menos un número.")
            )

        # Check for at least one symbol
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\'":\\|,.<>\/?]', password):
            errors.append(
                _("La contraseña debe contener al menos un símbolo especial.")
            )

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        """Return help text for the validator."""
        return _(
            "Su contraseña debe cumplir con los siguientes requisitos:\n"
            "- Mínimo 8 caracteres\n"
            "- Al menos una letra mayúscula\n"
            "- Al menos un número\n"
            "- Al menos un símbolo especial (!@#$%^&*()_+-=[]{};':\"\\|,.<>/?)\n"
            "Ejemplo: Abcdef1!"
        )
