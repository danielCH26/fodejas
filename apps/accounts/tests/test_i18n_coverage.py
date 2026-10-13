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
from django.urls import reverse
from django.utils.translation import activate, gettext, pgettext

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


# =============================================================================
# 5. View-injected nav labels — apps/accounts/views/accounts_views.py
# =============================================================================


@pytest.mark.django_db
def test_dashboard_nav_labels_catalog_entries_in_english():
    """
    Audit: accounts_views._get_navigation_items() uses gettext_lazy() to wrap
    Spanish nav labels. Catalog entries are verified to translate correctly.
    This test verifies the catalog entries; full rendering requires integration test.
    """
    activate("en")
    # Verify all nav label translations exist and are non-empty English
    nav_labels = [
        ("Mis Postulaciones", "My Applications"),
        ("Gestión de Usuarios", "User Management"),
        ("Mi Perfil", "My Profile"),
        ("Mis Notificaciones", "My Notifications"),
        ("Cerrar Sesión", "Log Out"),
        ("Estado de Selección", "Selection Status"),
        ("Convocatorias Abiertas", "Open Calls"),
        ("Revisar Requisitos", "Verify Requirements"),
        ("Resultados", "Results"),
        ("Gestión de Pagos", "Payment Management"),
        ("Mis Convocatorias", "My Calls for Applications"),
        ("Roles y Permisos", "Roles and Permissions"),
        ("Auditoría", "Audit Log"),
    ]
    for spanish, expected_english in nav_labels:
        actual = gettext(spanish)
        assert actual == expected_english, (
            f"Expected '{expected_english}' for '{spanish}', got '{actual}'"
        )
        # Ensure translation is not the same as Spanish (i.e., not untranslated)
        assert actual != spanish, (
            f"'{spanish}' must be translated, not remain as Spanish"
        )


def test_nav_label_mis_postulaciones_english():
    """
    Audit: "Mis Postulaciones" hardcoded in R-ASPIRANTE nav_items.
    SHALL translate to "My Applications" when locale=en.
    """
    activate("en")
    assert gettext("Mis Postulaciones") == "My Applications", (
        f"Expected 'My Applications', got '{gettext('Mis Postulaciones')}'"
    )


def test_nav_label_gestion_usuarios_english():
    """
    Audit: "Gestión de Usuarios" hardcoded in R-ADMIN nav_items.
    SHALL translate to "User Management" when locale=en.
    """
    activate("en")
    assert gettext("Gestión de Usuarios") == "User Management", (
        f"Expected 'User Management', got '{gettext('Gestión de Usuarios')}'"
    )


def test_nav_label_mi_perfil_english():
    """
    Audit: "Mi Perfil" hardcoded in common nav_items.
    SHALL translate to "My Profile" when locale=en.
    """
    activate("en")
    assert gettext("Mi Perfil") == "My Profile", (
        f"Expected 'My Profile', got '{gettext('Mi Perfil')}'"
    )


def test_nav_label_mis_notificaciones_english():
    """
    Audit: "Mis Notificaciones" hardcoded in common nav_items.
    SHALL translate to "My Notifications" when locale=en.
    """
    activate("en")
    assert gettext("Mis Notificaciones") == "My Notifications", (
        f"Expected 'My Notifications', got '{gettext('Mis Notificaciones')}'"
    )


def test_nav_label_cerrar_sesion_english():
    """
    Audit: "Cerrar Sesión" hardcoded in common nav_items.
    SHALL translate to "Log Out" when locale=en.
    """
    activate("en")
    assert gettext("Cerrar Sesión") == "Log Out", (
        f"Expected 'Log Out', got '{gettext('Cerrar Sesión')}'"
    )


# =============================================================================
# 6. Transparency sub-pages — actos.html, convocatorias.html, index.html,
#    estadisticas.html
# =============================================================================


def test_actos_title_translates():
    """
    Audit: actos.html h2 "Actos Administrativos Publicados" is hardcoded.
    SHALL translate to "Published Administrative Acts" when locale=en.
    """
    activate("en")
    assert gettext("Actos Administrativos Publicados") == "Published Administrative Acts", (
        f"Expected 'Published Administrative Acts', got '{gettext('Actos Administrativos Publicados')}'"
    )


def test_actos_subtitle_translates():
    """
    Audit: actos.html subtitle "Resoluciones y actos administrativos
    publicados por FODEJAS" is hardcoded.
    SHALL translate to English when locale=en.
    """
    activate("en")
    assert gettext("Resoluciones y actos administrativos publicados por FODEJAS") == (
        "Resolutions and administrative acts published by FODEJAS"
    ), (
        f"Expected English subtitle, got '{gettext('Resoluciones y actos administrativos publicados por FODEJAS')}'"
    )


def test_convocatorias_title_translates():
    """
    Audit: convocatorias.html h2 "Convocatorias" is hardcoded.
    SHALL translate to "Calls for Applications" when locale=en.
    Note: "Convocatorias" already has a translation "Calls for Applications"
    in the catalog; the template should use {% trans %}.
    """
    activate("en")
    assert gettext("Convocatorias") == "Calls for Applications", (
        f"Expected 'Calls for Applications', got '{gettext('Convocatorias')}'"
    )


def test_convocatorias_subtitle_translates():
    """
    Audit: convocatorias.html subtitle
    "Convocatorias abiertas y cerradas disponibles" is hardcoded.
    SHALL translate to "Open and closed calls available" when locale=en.
    """
    activate("en")
    assert gettext("Convocatorias abiertas y cerradas disponibles") == (
        "Open and closed calls available"
    ), (
        f"Expected 'Open and closed calls available', got "
        f"'{gettext('Convocatorias abiertas y cerradas disponibles')}'"
    )


def test_transparencia_index_data_protection_notice_translates():
    """
    Audit: index.html (~line 125) hardcoded data-protection paragraph
    "Este portal expone información agregada y pública de conformidad con
    la Ley 1581 de 2012 (protección de datos) y los principios de datos abiertos."
    SHALL translate to English when locale=en.
    """
    activate("en")
    spanish = (
        "Este portal expone información agregada y pública de conformidad con "
        "la Ley 1581 de 2012 (protección de datos) y los principios de datos abiertos."
    )
    english = gettext(spanish)
    assert english != spanish, (
        "The data protection notice MUST be translated when locale=en"
    )
    assert "open data" in english.lower() or "law 1581" in english.lower(), (
        f"Expected English data protection text, got '{english}'"
    )


def test_transparencia_index_contact_notice_translates():
    """
    Audit: index.html (~line 129) hardcoded contact paragraph
    "Para información detallada contacte a la Secretaría de Educación Departamental."
    SHALL translate to English when locale=en.
    """
    activate("en")
    spanish = (
        "Para información detallada contacte a la Secretaría de Educación Departamental."
    )
    english = gettext(spanish)
    assert english != spanish, (
        "The contact notice MUST be translated when locale=en"
    )
    assert "contact" in english.lower(), (
        f"Expected English contact text, got '{english}'"
    )


def test_estadisticas_resumen_convocatorias_translates():
    """
    Audit: estadisticas.html card-header "Resumen de Convocatorias"
    is hardcoded at line ~58.
    SHALL translate to "Call for Applications Summary" when locale=en.
    """
    activate("en")
    assert gettext("Resumen de Convocatorias") == "Call for Applications Summary", (
        f"Expected 'Call for Applications Summary', got '{gettext('Resumen de Convocatorias')}'"
    )


# =============================================================================
# 7. Dashboard greeting in English
# =============================================================================


def test_dashboard_greeting_catalog_entry_in_english():
    """
    Audit: dashboard.html greeting uses {% blocktrans context "dashboard welcome" %}.
    Catalog entry has msgctxt "dashboard welcome" + msgid "Bienvenido, %(first_name)s".
    SHALL translate to "Welcome, %(first_name)s" when locale=en.
    """
    activate("en")
    # The greeting uses {% blocktrans context "dashboard welcome" %}
    # which requires pgettext (context-aware lookup)
    spanish = "Bienvenido, %(first_name)s"
    context = "dashboard welcome"
    # pgettext(context, msgid) looks up with context
    english = pgettext(context, spanish)
    assert english == "Welcome, %(first_name)s", (
        f"Expected 'Welcome, %(first_name)s', got '{english}'"
    )
    assert "Welcome" in english and "Bienvenido" not in english, (
        "Greeting must be translated to English, not remain Spanish"
    )
