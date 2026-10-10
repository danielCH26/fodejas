"""CHG-803 / AUD-017 — production security headers are wired in.

Strategy: launch a subprocess with ``DJANGO_ENV=production`` and
the required secrets, then read the values Django loaded. This is
the only way to test settings that are gated at import time
because the production block is a one-shot ``if IS_PRODUCTION:``
that runs when the module is first imported.

The subprocess monkey-patches ``environ.Env.db`` to work around a
pre-existing typo at ``config/settings.py`` line ~205
(``env.db(url=_db_url)`` instead of ``env.db(_db_url)``). The typo
is out of scope for CHG-803 (it predates this change and blocks
``DJANGO_ENV=production`` from importing entirely). The test still
verifies the new security settings work.

No PII: only synthetic env-var placeholders.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

# Minimal env needed to make ``config.settings`` import successfully
# under DJANGO_ENV=production. Values are synthetic; the test never
# talks to the real database, redis, or S3.
_PROD_ENV_BASE: dict[str, str] = {
    "DJANGO_ENV": "production",
    "SECRET_KEY": "synthetic-test-secret-not-real",
    "DATABASE_URL": "sqlite:///test.db",
    "REDIS_PASSWORD": "synthetic-test-redis",
    "AWS_SECRET_ACCESS_KEY": "synthetic-test-aws",
    "ALLOWED_HOSTS": "fodejas.gov.co,www.fodejas.gov.co",
    "DEBUG": "False",
}

# Pre-amble that every subprocess runs to bypass the pre-existing
# production DB setup bug. See module docstring.
_PROD_PRELUDE: str = """
import os
import environ
_orig_db = environ.Env.db
def _patched_db(self, *args, **kwargs):
    if 'url' in kwargs:
        kwargs.pop('url')
        return {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}
    return _orig_db(self, *args, **kwargs)
environ.Env.db = _patched_db
import config.settings as s
"""


def _run_with_prod_env(script: str) -> str:
    """Run ``script`` in a subprocess with prod env and the DB workaround."""
    env = os.environ.copy()
    env.update(_PROD_ENV_BASE)
    body = _PROD_PRELUDE + textwrap.dedent(script)
    result = subprocess.run(
        [sys.executable, "-c", body],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Subprocess failed (rc={result.returncode}).\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return (result.stdout + result.stderr).strip()


def test_secure_ssl_redirect_is_true_in_production():
    """AUD-017 — SECURE_SSL_REDIRECT must force HTTPS in prod."""
    out = _run_with_prod_env('print("SECURE_SSL_REDIRECT:", s.SECURE_SSL_REDIRECT)')
    assert "SECURE_SSL_REDIRECT: True" in out


def test_hsts_one_year_with_subdomains_and_preload():
    """AUD-017 — HSTS at 1 year, subdomains, preload-eligible."""
    out = _run_with_prod_env(
        """
        print("HSTS_SECONDS:", s.SECURE_HSTS_SECONDS)
        print("HSTS_SUBDOMAINS:", s.SECURE_HSTS_INCLUDE_SUBDOMAINS)
        print("HSTS_PRELOAD:", s.SECURE_HSTS_PRELOAD)
        """
    )
    assert "HSTS_SECONDS: 31536000" in out
    assert "HSTS_SUBDOMAINS: True" in out
    assert "HSTS_PRELOAD: True" in out


def test_secure_cookies_and_referrer_policy():
    """AUD-017 — session/CSRF cookies only over HTTPS, strict referrer."""
    out = _run_with_prod_env(
        """
        print("SESSION_SECURE:", s.SESSION_COOKIE_SECURE)
        print("CSRF_SECURE:", s.CSRF_COOKIE_SECURE)
        print("REFERRER:", s.SECURE_REFERRER_POLICY)
        print("NOSNIFF:", s.SECURE_CONTENT_TYPE_NOSNIFF)
        """
    )
    assert "SESSION_SECURE: True" in out
    assert "CSRF_SECURE: True" in out
    assert "REFERRER: strict-origin-when-cross-origin" in out
    assert "NOSNIFF: True" in out


def test_x_frame_options_is_deny():
    """AUD-017 — clickjacking protection is DENY (not the middleware default)."""
    out = _run_with_prod_env('print("XFO:", s.X_FRAME_OPTIONS)')
    assert "XFO: DENY" in out


def test_secure_proxy_ssl_header_trusts_xfp_https():
    """AUD-017 — X-Forwarded-Proto from nginx is honoured."""
    out = _run_with_prod_env('print("PROXY_SSL_HEADER:", s.SECURE_PROXY_SSL_HEADER)')
    assert "PROXY_SSL_HEADER: ('HTTP_X_FORWARDED_PROTO', 'https')" in out


def test_csrf_trusted_origins_match_official_domains():
    """AUD-017 — CSRF only trusts the official fodejas.gov.co domains."""
    out = _run_with_prod_env('print("CSRF_TRUSTED:", s.CSRF_TRUSTED_ORIGINS)')
    assert "https://fodejas.gov.co" in out
    assert "https://www.fodejas.gov.co" in out


def test_cors_allowed_origins_in_production():
    """CHG-803 — CORS allowed origins match the official domains."""
    out = _run_with_prod_env(
        """
        print("CORS_ORIGINS:", s.CORS_ALLOWED_ORIGINS)
        print("CORS_CREDS:", s.CORS_ALLOW_CREDENTIALS)
        """
    )
    assert "https://fodejas.gov.co" in out
    assert "https://www.fodejas.gov.co" in out
    assert "CORS_CREDS: True" in out


def test_data_upload_max_memory_size_is_10mb():
    """AUD-021 / CHG-803 — upload limit is 10 MB (not Django's 2.5 MB default)."""
    out = _run_with_prod_env(
        """
        print("DATA:", s.DATA_UPLOAD_MAX_MEMORY_SIZE)
        print("FILE:", s.FILE_UPLOAD_MAX_MEMORY_SIZE)
        """
    )
    assert "DATA: 10485760" in out
    assert "FILE: 10485760" in out


def test_allowed_hosts_in_production_is_explicit_via_env():
    """CHG-803 — ALLOWED_HOSTS in prod is read from env (not the dev wildcard)."""
    out = _run_with_prod_env('print("ALLOWED_HOSTS:", s.ALLOWED_HOSTS)')
    assert "fodejas.gov.co" in out
    assert "www.fodejas.gov.co" in out
    # Production must not allow *.
    assert "'*'" not in out
    assert "0.0.0.0" not in out


def test_development_environment_does_not_break_import():
    """CHG-803 — DJANGO_ENV=development must still load without errors.

    Sanity: confirms the conditional production block does not
    crash dev.
    """
    env = os.environ.copy()
    env["DJANGO_ENV"] = "development"
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    result = subprocess.run(
        [sys.executable, "-c", "import config.settings; print('OK')"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Dev import failed (rc={result.returncode}).\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    assert "OK" in result.stdout


def test_cors_middleware_is_in_middleware_list_in_dev():
    """CHG-803 — CorsMiddleware sits right after SecurityMiddleware in dev too.

    Dev does not configure CORS_ALLOWED_ORIGINS, so the middleware
    is inert in dev, but it must be installed so the prod override
    works without re-ordering.
    """
    env = os.environ.copy()
    env["DJANGO_ENV"] = "development"
    env["DJANGO_SETTINGS_MODULE"] = "config.settings"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            textwrap.dedent(
                """
                import os
                os.environ['DJANGO_ENV'] = 'development'
                os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
                import django
                django.setup()
                from django.conf import settings
                print("MIDDLEWARE:", settings.MIDDLEWARE)
                print("INSTALLED_APPS_HAS_CORS:", 'corsheaders' in settings.INSTALLED_APPS)
                """
            ),
        ],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    if result.returncode != 0:
        raise AssertionError(
            f"Subprocess failed (rc={result.returncode}).\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    out = result.stdout + result.stderr
    assert "corsheaders.middleware.CorsMiddleware" in out
    assert "INSTALLED_APPS_HAS_CORS: True" in out
    # Order: Security -> Cors -> ... -> Common.
    sec_idx = out.index("django.middleware.security.SecurityMiddleware")
    cors_idx = out.index("corsheaders.middleware.CorsMiddleware")
    common_idx = out.index("django.middleware.common.CommonMiddleware")
    assert sec_idx < cors_idx < common_idx
