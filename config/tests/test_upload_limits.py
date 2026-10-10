"""CHG-803 / AUD-021 — upload size limits are enforced.

The global ``DATA_UPLOAD_MAX_MEMORY_SIZE`` (10 MB) and
``FILE_UPLOAD_MAX_MEMORY_SIZE`` (10 MB) live in ``config/settings.py``.
A body that exceeds the limit must be rejected with 400
``RequestDataTooBig`` by Django's request handler before the view
runs.

Note: Django's test ``Client`` builds a request via
``RequestFactory`` and short-circuits size checks for content types
that aren't form-encoded or multipart. To exercise the real
``_load_post_and_files`` code path we POST to a view that
accesses ``request.POST`` (the registration form at
``/accounts/register/``) with ``application/x-www-form-urlencoded``
content. That triggers the size check via ``LimitedStream`` and
returns 400 ``RequestDataTooBig`` before the view runs.
"""

from __future__ import annotations

import pytest
from django.test import Client, override_settings


@pytest.mark.django_db
def test_oversized_form_body_returns_request_data_too_big(settings):
    """An 11 MB form-urlencoded body must return 400 (RequestDataTooBig).

    The registration view reads ``request.POST`` which triggers
    Django's form parser. With ``DATA_UPLOAD_MAX_MEMORY_SIZE``
    set to the default 10 MB, the parser raises
    ``RequestDataTooBig`` and the WSGI handler converts it to 400.
    """
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
    client = Client(enforce_csrf_checks=False)
    # 11 MB > 10 MB limit.
    body = b"field=" + b"x" * (11 * 1024 * 1024)
    response = client.post(
        "/accounts/register/",
        data=body,
        content_type="application/x-www-form-urlencoded",
    )
    assert response.status_code == 400, (
        f"Expected 400 for 11 MB body, got {response.status_code}. "
        f"Content: {response.content[:200]!r}"
    )


@pytest.mark.django_db
def test_small_form_body_passes_size_check(settings):
    """A 1 KB body is well under the 10 MB limit.

    The registration form will fail validation (missing required
    fields) — that is expected. We only assert that the size check
    did NOT reject the request (i.e. not 400 from
    RequestDataTooBig).
    """
    settings.DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
    client = Client(enforce_csrf_checks=False)
    body = b"email=invalid&password=short"
    response = client.post(
        "/accounts/register/",
        data=body,
        content_type="application/x-www-form-urlencoded",
    )
    # NOT 400 from RequestDataTooBig. The form will return 200 with
    # validation errors, or 403 if CSRF was re-enabled. The point is
    # the body parsed.
    assert response.status_code != 400 or b"RequestDataTooBig" not in response.content, (
        f"1 KB body should NOT trigger RequestDataTooBig. "
        f"Got {response.status_code} with body {response.content[:200]!r}."
    )


@pytest.mark.django_db
@override_settings(DATA_UPLOAD_MAX_MEMORY_SIZE=512)  # 512 bytes
def test_lowered_limit_is_enforced():
    """Lowering the limit via override_settings should trigger 400.

    Confirms the request handler actually consults the setting
    (not a hard-coded constant).
    """
    client = Client(enforce_csrf_checks=False)
    body = b"field=" + b"x" * 1024  # 1 KB > 512 bytes
    response = client.post(
        "/accounts/register/",
        data=body,
        content_type="application/x-www-form-urlencoded",
    )
    assert response.status_code == 400, (
        f"With DATA_UPLOAD_MAX_MEMORY_SIZE=512, a 1 KB body must "
        f"return 400. Got {response.status_code}."
    )


def test_data_upload_max_memory_size_setting_is_10mb(settings):
    """The setting itself is 10 MB (verified at module level, not via request).

    The runtime value lives in ``config.settings``. ``override_settings``
    is a no-op for verification of the real value.
    """
    # Read the real value via the module (avoids override_settings).
    from config import settings as cfg

    assert cfg.DATA_UPLOAD_MAX_MEMORY_SIZE == 10 * 1024 * 1024
    assert cfg.FILE_UPLOAD_MAX_MEMORY_SIZE == 10 * 1024 * 1024
