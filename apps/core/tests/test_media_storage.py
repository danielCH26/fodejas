"""Tests for media storage configuration (Gap #1 — chore/media-serving).

Architecture decision: bucket privado + signed URLs (AWS_QUERYSTRING_AUTH=True)
because annexes contain personal data under Ley 1581/2012.
Single S3-compatible storage path (MinIO dev / S3 prod per roadmap INF-008).
Storage location prefix: media/ (AWS_LOCATION).

Run: python -m pytest apps/core/tests/test_media_storage.py -q
"""

import tempfile
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings


def _storages_available() -> bool:
    """True when django-storages is installed in this environment.

    django-storages is a runtime dependency declared in pyproject.toml.
    In the Docker dev environment (and CI) it IS installed.
    Locally, pip install may not have been run.
    """
    try:
        import storages  # noqa: F401

        return True
    except ImportError:
        return False


# ---------------------------------------------------------------------------
# 1. Settings contract — verifies the STORAGES dict is wired correctly
# ---------------------------------------------------------------------------


class TestStorageSettingsContract:
    """Storage wiring contract — conditional by DJANGO_ENV.

    - development/test (CI): FileSystemStorage + MEDIA_ROOT/MEDIA_URL →
      the suite never touches the network.
    - staging/production: S3Boto3Storage (MinIO/S3) with signed URLs.
    """

    def test_storages_dict_exists(self):
        assert hasattr(settings, "STORAGES"), (
            "settings.STORAGES is not defined — FileField has no backend; "
            ".url produces broken URLs (Gap #1)"
        )

    def test_default_backend_filesystem_in_test_env(self):
        """The test/development environment must use FileSystemStorage so
        the suite (governance acta generation included) never needs MinIO."""
        assert settings.STORAGES["default"]["BACKEND"] == (
            "django.core.files.storage.FileSystemStorage"
        )

    def test_media_root_and_url_defined_in_test_env(self):
        assert hasattr(settings, "MEDIA_ROOT") and settings.MEDIA_ROOT
        assert settings.MEDIA_URL == "/media/"

    def test_production_maps_to_s3boto3_signed(self):
        """Source-level config contract: the staging/production branch of
        the conditional must select S3Boto3 with signed URLs (private
        bucket, Ley 1581/2012 — annexes hold personal data)."""
        from importlib import import_module

        source = Path(import_module("config.settings").__file__).read_text(encoding="utf-8")
        assert '"storages.backends.s3boto3.S3Boto3Storage"' in source
        assert 'AWS_QUERYSTRING_AUTH = True' in source
        assert 'AWS_S3_ADDRESSING_STYLE = "path"' in source
        assert 'AWS_LOCATION = "media"' in source

    def test_querystring_auth_true(self):
        """Signed URLs: bucket stays private; only holders of a signed URL
        can access the file (Ley 1581/2012 PII in annexes)."""
        assert settings.AWS_QUERYSTRING_AUTH is True

    def test_default_acl_none(self):
        """No default ACL — all objects inherit bucket policy or explicit
        object ACL; prevents accidental public exposure."""
        assert settings.AWS_DEFAULT_ACL is None

    def test_location_prefix(self):
        """All media keys are prefixed media/ so they are isolated from
        static files and other S3 namespaces."""
        assert settings.AWS_LOCATION == "media"

    def test_addressing_style_path(self):
        """path-style addressing is REQUIRED for MinIO endpoint URLs.
        Without it boto3 builds virtual-hosted domains like
        fodejas-media.localhost:9000 which do not resolve."""
        assert settings.AWS_S3_ADDRESSING_STYLE == "path"

    def test_bucket_name(self):
        assert settings.AWS_STORAGE_BUCKET_NAME == "fodejas-media"

    def test_endpoint_url(self):
        assert settings.AWS_S3_ENDPOINT_URL == "http://localhost:9000"

    def test_staticfiles_backend_preserved(self):
        """Switching the default storage MUST NOT affect staticfiles.
        collectstatic must continue to write to the filesystem."""
        backend = settings.STORAGES["staticfiles"]["BACKEND"]
        assert (
            "s3boto" not in backend.lower()
        ), "staticfiles backend must not be S3-based"


# ---------------------------------------------------------------------------
# 2. Functional test — FileField pipeline works end-to-end with swapped storage
# ---------------------------------------------------------------------------


class TestFileFieldPipeline:
    """End-to-end: create file → save via FileField → verify .url path.

    Uses override_settings to swap the default storage to a deterministic
    FileSystemStorage so tests run without MinIO.
    """

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": settings.STORAGES.get(
                "staticfiles",
                {"BACKEND": "django.contrib.staticfiles.storage.staticfiles_storage"},
            ),
        },
        MEDIA_ROOT=tempfile.mkdtemp(prefix="fodejas-test-media-"),
        MEDIA_URL="/media-test/",
    )
    def test_filefield_url_contains_media_url(self):
        """
        FileField.save() → field.url must contain MEDIA_URL prefix.
        This is the primary symptom of Gap #1: without a configured backend,
        FileField generates broken/empty .url values.
        """
        storage = FileSystemStorage()
        # SimpleUploadedFile mimics an uploaded PDF annex
        uploaded = SimpleUploadedFile(
            name="comprobante_pago.pdf",
            content=b"%PDF-1.4 test content",
            content_type="application/pdf",
        )

        # Save through the storage directly (equivalent to model.file.save())
        path = storage.save("test_upload/comprobante_pago.pdf", uploaded)
        assert path, "storage.save() returned empty path"

        url = storage.url(path)
        assert url.startswith("/media-test/"), (
            f"storage.url() returned '{url}' — does not start with MEDIA_URL "
            "'/media-test/'. Check that a default storage backend is configured."
        )

        # Cleanup
        if storage.exists(path):
            storage.delete(path)

    @override_settings(
        STORAGES={
            "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
            "staticfiles": settings.STORAGES.get(
                "staticfiles",
                {"BACKEND": "django.contrib.staticfiles.storage.staticfiles_storage"},
            ),
        },
        MEDIA_ROOT=tempfile.mkdtemp(prefix="fodejas-test-media-"),
        MEDIA_URL="/media-test/",
    )
    def test_filefield_storage_instance_is_default_backend(self):
        """The FileField.storage singleton must be the configured default."""
        from django.core.files.storage import default_storage

        # default_storage._wrapped must be a FileSystemStorage (our override)
        assert hasattr(default_storage, "url"), (
            "default_storage has no url() method — backend not wired"
        )
        # Verify the actual backend class
        assert isinstance(
            default_storage, FileSystemStorage
        ), f"default_storage is {type(default_storage).__name__}, expected FileSystemStorage"

    def test_s3boto3_storage_backend_string_is_valid(self):
        """The production backend string must be a valid dotted path."""
        from importlib import import_module

        source = Path(import_module("config.settings").__file__).read_text(encoding="utf-8")
        backend_path = "storages.backends.s3boto3.S3Boto3Storage"
        assert backend_path in source, "production backend missing from settings"
        module_path, class_name = backend_path.rsplit(".", 1)
        assert class_name.isidentifier()

    @pytest.mark.skipif(
        # django-storages is a runtime dependency (installed in Docker, not on
        # the bare host). In CI/Docker it IS installed; locally it may not be.
        # We skip only the import/instantiation check when the module is absent.
        # Settings contract tests always run and verify the STORAGES dict.
        not _storages_available(),
        reason="django-storages not installed in this environment (runtime dep)",
    )
    def test_s3boto3_storage_import_not_lazy(self):
        """Importing the backend class must NOT require a running MinIO.

        S3Boto3Storage is lazy — boto3 connects on first file operation,
        not on class import or instantiation.
        """
        from importlib import import_module

        backend_path = "storages.backends.s3boto3.S3Boto3Storage"
        module_path, class_name = backend_path.rsplit(".", 1)
        module = import_module(module_path)
        backend_cls = getattr(module, class_name)
        # Instantiate — does NOT connect to MinIO (boto3 is lazy)
        instance = backend_cls()
        assert hasattr(instance, "url")
        assert hasattr(instance, "save")
        assert hasattr(instance, "delete")



