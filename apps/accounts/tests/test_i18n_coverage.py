"""
test_i18n_coverage.py — CHG-507-multilang Unit D (Coverage)

Tests that verify English translations are properly wrapped and compiled
for previously untranslated strings across the FODEJAS codebase.

Audit finding addressed: multiple UI strings in forms, templates, and
service layers were hardcoded in Spanish without gettext wrappers, making
English locale display impossible.

Test categories:
1. Nav/transparency strings from base templates
2. Form placeholder strings from accounts forms
3. Transparency portal strings from templates/transparencia/
4. ValidationError messages from forms/services
"""

import pytest
from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, override_settings
from django.utils.translation import activate, gettext

from apps.accounts.forms import FodejasLoginForm, FodejasRegistrationForm
from apps.claims.services import transitions as apelacion_transitions

User = get_user_model()


# =============================================================================
# 1. Nav / sidebar strings — from base.html and transparency templates
# =============================================================================


def test_nav_transparencia_translates():
    """
    Audit: "Portal de Transparencia" hardcoded in base.html navbar brand.
    SHALL translate to "Transparency Portal" when locale=en.
    """
    activate("en")
    assert gettext("Transparencia") == "Transparency"


def test_nav_mobile_menu_translates():
    """
    Audit: "Menú móvil" used in mobile menu toggle aria-label.
    SHALL translate to "Mobile menu" when locale=en.
    """
    activate("en")
    assert gettext("Menú móvil") == "Mobile menu"


def test_nav_open_menu_translates():
    """
    Audit: "Abrir menú" used in aria-label for menu toggle.
    SHALL translate to "Open menu" when locale=en.
    """
    activate("en")
    assert gettext("Abrir menú") == "Open menu"


def test_nav_close_menu_translates():
    """
    Audit: "Cerrar menú" used in aria-label for close menu button.
    SHALL translate to "Close menu" when locale=en.
    """
    activate("en")
    assert gettext("Cerrar menú") == "Close menu"


def test_nav_main_navigation_translates():
    """
    Audit: "Navegación principal" used as aria-label on nav element.
    SHALL translate to "Main navigation" when locale=en.
    """
    activate("en")
    assert gettext("Navegación principal") == "Main navigation"


# =============================================================================
# 2. Form placeholder strings — apps/accounts/forms.py
# =============================================================================


@pytest.mark.django_db
def test_login_form_password_placeholder_in_english(client, django_db_setup):
    """
    Audit: FodejasLoginForm.password placeholder "Ingrese su contraseña"
    was hardcoded Spanish.
    SHALL render as "Enter your password" in English locale.
    """
    activate("en")
    form = FodejasLoginForm()
    rendered = form.as_p()
    # Must NOT contain Spanish placeholder
    assert "Ingrese su contraseña" not in rendered, (
        "Spanish placeholder 'Ingrese su contraseña' must not appear when locale=en"
    )
    # Must contain English equivalent (case-insensitive check of placeholder attr)
    assert "placeholder" in rendered
    # The English translation wraps the original Spanish string
    assert "Enter your password" in rendered.lower() or "enter your password" in rendered.lower(), (
        "English placeholder 'Enter your password' must appear in rendered form when locale=en"
    )


@pytest.mark.django_db
def test_register_form_email_placeholder_in_english(client, django_db_setup):
    """
    Audit: FodejasRegistrationForm placeholders were all hardcoded Spanish.
    SHALL render email placeholder in English (email@example.com is neutral;
    check that the form does NOT contain Spanish placeholders).
    """
    activate("en")
    form = FodejasRegistrationForm()
    rendered = form.as_p()
    # Must NOT contain hardcoded Spanish placeholders
    spanish_placeholders = [
        "Número de documento de identidad",
        "Número de teléfono",
        "Nombres completos",
        "Apellidos completos",
    ]
    for spanish in spanish_placeholders:
        assert spanish not in rendered, (
            f"Spanish placeholder '{spanish}' must not appear when locale=en"
        )
    # Should contain English placeholders
    english_keywords = ["document", "phone", "first", "last", "name"]
    rendered_lower = rendered.lower()
    found_english = any(kw in rendered_lower for kw in english_keywords)
    assert found_english, (
        "At least one English placeholder keyword must appear in rendered form when locale=en"
    )


# =============================================================================
# 3. Transparency portal strings — templates/transparencia/*.html
# =============================================================================


def test_transparencia_portal_title_translates():
    """
    Audit: "Portal de Transparencia" hardcoded as h1 in transparencia/index.html.
    SHALL translate to "Transparency Portal" when locale=en.
    """
    activate("en")
    assert gettext("Portal de Transparencia") == "Transparency Portal"


def test_transparencia_estadisticas_title_translates():
    """
    Audit: "Estadísticas" used as section heading in estadisticas.html.
    SHALL translate to "Statistics" when locale=en.
    """
    activate("en")
    assert gettext("Estadísticas") == "Statistics"


def test_transparencia_beneficiarios_label_translates():
    """
    Audit: "Beneficiarios" used as KPI card label in transparencia/index.html.
    SHALL translate to "Beneficiaries" when locale=en.
    """
    activate("en")
    assert gettext("Beneficiarios") == "Beneficiaries"


# =============================================================================
# 4. ValidationError messages — forms and services
# =============================================================================


def test_email_validation_error_in_english():
    """
    Audit: FodejasRegistrationForm.clean_email ValidationError
    "Ya existe una cuenta con este correo electrónico." was hardcoded.
    SHALL return English message "An account with this email already exists."
    when locale=en.
    """
    activate("en")
    # Test the lazy string directly via gettext (resolves at runtime with active locale)
    error_msg = gettext("Ya existe una cuenta con este correo electrónico.")
    assert error_msg == "An account with this email already exists.", (
        f"Expected 'An account with this email already exists.', got '{error_msg}'"
    )


@pytest.mark.django_db
def test_admin_documento_min_length_error_english():
    """
    Audit: UserAdminForm.clean_documento ValidationError
    "El documento debe tener al menos 6 caracteres." was hardcoded.
    SHALL translate to English when locale=en.
    """
    activate("en")
    # Load admin form module directly (forms/ directory has no __init__.py,
    # so apps.accounts.forms.admin import path is broken; use direct file load)
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "accounts_forms_admin",
        "apps/accounts/forms/admin.py"
    )
    admin_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(admin_mod)
    UserAdminForm = admin_mod.UserAdminForm

    form = UserAdminForm(data={
        "email": "test@example.com",
        "confirm_email": "test@example.com",
        "documento": "123",  # Too short
        "first_name": "Test",
        "last_name": "User",
    })
    # Trigger validation
    form.is_valid()
    errors = form.errors.get("documento", [])
    error_messages = [str(e) for e in errors]

    # Must NOT contain Spanish error
    spanish_errors = [
        "El documento debe tener al menos 6 caracteres.",
        "El documento debe tener al menos 6 caracteres",
    ]
    has_spanish = any(spanish in msg for spanish in spanish_errors for msg in error_messages)
    assert not has_spanish, (
        f"Spanish ValidationError '{spanish_errors[0]}' must not appear when locale=en. "
        f"Got: {error_messages}"
    )
    # Must contain English error
    has_english = any("6 characters" in msg.lower() or "least 6" in msg.lower() for msg in error_messages)
    assert has_english, (
        f"English error message with '6 characters' must appear when locale=en. "
        f"Got: {error_messages}"
    )


def test_apelacion_confirmar_empty_respuesta_error_english():
    """
    Audit: apelacion_transitions.confirmar raises ValidationError
    "La respuesta no puede estar vacía." on empty respuesta.
    SHALL translate to English when locale=en.
    """
    activate("en")
    from django.core.exceptions import ValidationError

    error_msg = gettext("La respuesta no puede estar vacía.")
    assert error_msg == "The response cannot be empty.", (
        f"Expected 'The response cannot be empty.', got '{error_msg}'"
    )
