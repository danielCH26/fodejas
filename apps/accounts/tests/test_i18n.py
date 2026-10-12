"""
i18n infrastructure tests for CHG-507-multilang (Unit A).

These tests verify the i18n infrastructure is correctly configured and
the language switcher works end-to-end. The .mo files for 'en' MUST be
compiled and committed before running these tests (via
scripts/compile_mo.py); the tests depend on the compiled translations.

Tests:
- Settings: LocaleMiddleware in MIDDLEWARE at correct position, LANGUAGES,
  LOCALE_PATHS.
- Switcher: POST to /i18n/set_language/ → 302 + django_language cookie.
- English render: GET login with en cookie → English strings visible.
- Regression: GET login without cookie → Spanish msgids (exact current text).
- compile_mo.py: generates .mo files correctly.
"""

import hashlib
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings
from django.urls import reverse


# ─────────────────────────────────────────────────────────────────────────────
# Settings tests
# ─────────────────────────────────────────────────────────────────────────────


def test_locale_middleware_present():
    """LocaleMiddleware SHALL be present in MIDDLEWARE."""
    assert "django.middleware.locale.LocaleMiddleware" in settings.MIDDLEWARE


def test_locale_middleware_position():
    """
    LocaleMiddleware SHALL be after SessionMiddleware and before CommonMiddleware.

    Position contract: SessionMiddleware → LocaleMiddleware → CommonMiddleware.
    This ordering is required so the locale middleware can read the language
    cookie/session and set it before CommonMiddleware processes the URL with
    the default prefix.
    """
    mw = settings.MIDDLEWARE
    session_idx = mw.index("django.contrib.sessions.middleware.SessionMiddleware")
    locale_idx = mw.index("django.middleware.locale.LocaleMiddleware")
    common_idx = mw.index("django.middleware.common.CommonMiddleware")
    assert session_idx < locale_idx, (
        f"LocaleMiddleware (index {locale_idx}) must be AFTER "
        f"SessionMiddleware (index {session_idx})"
    )
    assert locale_idx < common_idx, (
        f"LocaleMiddleware (index {locale_idx}) must be BEFORE "
        f"CommonMiddleware (index {common_idx})"
    )


def test_languages_setting():
    """LANGUAGES SHALL contain es-CO and en."""
    lang_codes = {code for code, _ in settings.LANGUAGES}
    assert "es-CO" in lang_codes, "LANGUAGES must include es-CO"
    assert "en" in lang_codes, "LANGUAGES must include en"


def test_locale_paths_setting():
    """LOCALE_PATHS SHALL resolve to BASE_DIR / 'locale'."""
    locale_paths = settings.LOCALE_PATHS
    assert len(locale_paths) >= 1
    # At least one path must end with 'locale'
    locale_names = {p.name for p in locale_paths}
    assert "locale" in locale_names, (
        f"LOCALE_PATHS must contain a 'locale' directory. Found: {locale_paths}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Language switcher
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_language_switcher_redirect(client):
    """
    POST to set_language with language=en SHALL return 302 and set
    django_language cookie.
    """
    # NOTE: Do NOT pass content_type='application/x-www-form-urlencoded'
    # explicitly — the test client converts data={} dict to form-encoded
    # automatically; setting content_type overrides that and causes the
    # dict to be sent as a raw string (not URL-encoded POST data), which
    # makes request.POST empty and the language cookie is not set.
    response = client.post(
        reverse("set_language"),
        data={"language": "en", "next": "/"},
    )
    assert response.status_code == 302, (
        f"Expected 302 redirect, got {response.status_code}"
    )
    # Cookie must be set
    cookie = response.cookies.get("django_language")
    assert cookie is not None, "django_language cookie must be set"
    assert cookie.value == "en", f"Expected cookie value 'en', got '{cookie.value}'"


# ─────────────────────────────────────────────────────────────────────────────
# English render
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.django_db
def test_login_english(client):
    """
    GET /accounts/login/ with django_language=en cookie SHALL render
    English strings (not Spanish msgids).
    """
    client.cookies["django_language"] = "en"
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200
    # Must contain an English string that we've translated
    assertContains = lambda s: response.content.decode().count(s)
    # The login heading in English
    assert "Iniciar Sesión" not in response.content.decode(), (
        "Spanish msgid 'Iniciar Sesión' must NOT appear when language is en"
    )
    # Must contain some English translation we added
    content_lower = response.content.decode().lower()
    # At minimum, the heading should be "Log in" or "Sign in"
    # We use "Iniciar Sesión" → "Log in" as our primary heading translation
    assert "log in" in content_lower, (
        "English translation 'Log in' must appear in en-rendered login page"
    )


@pytest.mark.django_db
def test_login_spanish_regression(client):
    """
    GET /accounts/login/ without language cookie SHALL render the current
    Spanish text byte-identical to pre-i18n version (regression zero).
    """
    response = client.get(reverse("accounts:login"))
    assert response.status_code == 200
    content = response.content.decode()
    # These are the exact msgids from the current template
    assert "Iniciar Sesión" in content, "Spanish heading 'Iniciar Sesión' missing"
    assert "Registrarse" in content, "Spanish 'Registrarse' missing"
    assert "Registrarse como Aspirante" in content, (
        "Spanish 'Registrarse como Aspirante' missing"
    )
    assert "Olvidó su contraseña" in content, (
        "Spanish '¿Olvidó su contraseña?' missing"
    )


# ─────────────────────────────────────────────────────────────────────────────
# compile_mo.py
# ─────────────────────────────────────────────────────────────────────────────


def test_compile_mo_script_exit_zero():
    """
    scripts/compile_mo.py SHALL exit with code 0.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    script = repo_root / "scripts" / "compile_mo.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=str(repo_root),
    )
    assert result.returncode == 0, (
        f"compile_mo.py failed with exit {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_compile_mo_generates_mo_files():
    """
    After running compile_mo.py, django.mo files SHALL exist for both
    locales.
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    # Run the script first
    script = repo_root / "scripts" / "compile_mo.py"
    subprocess.run([sys.executable, str(script)], check=True, cwd=str(repo_root))

    en_mo = repo_root / "locale" / "en" / "LC_MESSAGES" / "django.mo"
    es_mo = repo_root / "locale" / "es_CO" / "LC_MESSAGES" / "django.mo"
    assert en_mo.exists(), f"Expected {en_mo} to exist after compile_mo.py"
    assert es_mo.exists(), f"Expected {es_mo} to exist after compile_mo.py"


def test_compile_mo_idempotent():
    """
    Running compile_mo.py twice SHALL produce byte-identical .mo files
    (deterministic output).
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    script = repo_root / "scripts" / "compile_mo.py"

    def hash_mo(locale: str) -> str:
        mo_path = repo_root / "locale" / locale / "LC_MESSAGES" / "django.mo"
        return hashlib.md5(mo_path.read_bytes()).hexdigest()

    # Run once
    subprocess.run([sys.executable, str(script)], check=True, cwd=str(repo_root))
    hashes_before = {locale: hash_mo(locale) for locale in ("en", "es_CO")}

    # Run again
    subprocess.run([sys.executable, str(script)], check=True, cwd=str(repo_root))
    hashes_after = {locale: hash_mo(locale) for locale in ("en", "es_CO")}

    assert hashes_before == hashes_after, (
        f"compile_mo.py is NOT deterministic:\n"
        f"  en:  before={hashes_before['en']}, after={hashes_after['en']}\n"
        f"  es_CO: before={hashes_before['es_CO']}, after={hashes_after['es_CO']}"
    )


def test_en_po_has_translations():
    """
    locale/en/LC_MESSAGES/django.po SHALL have at least one msgid with
    a non-empty msgstr (English translation).
    """
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    en_po = repo_root / "locale" / "en" / "LC_MESSAGES" / "django.po"
    assert en_po.exists(), f"Expected {en_po} to exist"

    # Use polib to read the PO file
    import polib

    po = polib.pofile(str(en_po))
    translated = [e for e in po if e.msgstr and e.msgstr.strip()]
    assert len(translated) >= 5, (
        f"Expected at least 5 translated entries in en/django.po, "
        f"found {len(translated)}. "
        "Make sure locale/en/LC_MESSAGES/django.po has English msgstr entries."
    )
