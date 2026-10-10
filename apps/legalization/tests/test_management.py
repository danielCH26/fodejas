"""Tests for check_signer_config management command (CHG-301)."""
from __future__ import annotations

import sys
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command


@pytest.mark.django_db
class TestCheckSignerConfig:
    """Tests for check_signer_config management command."""

    def test_command_exits_0_in_development_with_mock(self):
        """In development, mock provider exits 0."""
        with patch(
            "apps.legalization.management.commands.check_signer_config.settings"
        ) as mock_settings:
            mock_settings.DJANGO_ENV = "development"
            mock_settings.SIGNATURE_PROVIDER = "mock"
            stdout = StringIO()
            call_command("check_signer_config", stdout=stdout)
            assert "SIGNATURE_PROVIDER='mock'" in stdout.getvalue()

    def test_command_exits_0_in_development_with_local(self):
        """In development, local provider also exits 0."""
        with patch(
            "apps.legalization.management.commands.check_signer_config.settings"
        ) as mock_settings:
            mock_settings.DJANGO_ENV = "development"
            mock_settings.SIGNATURE_PROVIDER = "local"
            stdout = StringIO()
            call_command("check_signer_config", stdout=stdout)
            assert "SIGNATURE_PROVIDER='local'" in stdout.getvalue()

    def test_command_exits_0_in_staging_with_local(self):
        """In staging, local provider exits 0."""
        with patch(
            "apps.legalization.management.commands.check_signer_config.settings"
        ) as mock_settings:
            mock_settings.DJANGO_ENV = "staging"
            mock_settings.SIGNATURE_PROVIDER = "local"
            stdout = StringIO()
            call_command("check_signer_config", stdout=stdout)
            assert "correct for environment" in stdout.getvalue()

    def test_command_exits_0_in_production_with_local(self):
        """In production, local provider exits 0."""
        with patch(
            "apps.legalization.management.commands.check_signer_config.settings"
        ) as mock_settings:
            mock_settings.DJANGO_ENV = "production"
            mock_settings.SIGNATURE_PROVIDER = "local"
            stdout = StringIO()
            call_command("check_signer_config", stdout=stdout)
            assert "correct for environment" in stdout.getvalue()

    def test_command_exits_1_in_staging_with_mock(self):
        """In staging, mock provider exits 1 (non-zero = error)."""
        with patch(
            "apps.legalization.management.commands.check_signer_config.settings"
        ) as mock_settings:
            mock_settings.DJANGO_ENV = "staging"
            mock_settings.SIGNATURE_PROVIDER = "mock"
            stderr = StringIO()
            with pytest.raises(SystemExit) as exc_info:
                call_command("check_signer_config", stderr=stderr)
            assert exc_info.value.code == 1
            assert "NOT allowed" in stderr.getvalue()

    def test_command_exits_1_in_production_with_mock(self):
        """In production, mock provider exits 1 (non-zero = error)."""
        with patch(
            "apps.legalization.management.commands.check_signer_config.settings"
        ) as mock_settings:
            mock_settings.DJANGO_ENV = "production"
            mock_settings.SIGNATURE_PROVIDER = "mock"
            stderr = StringIO()
            with pytest.raises(SystemExit) as exc_info:
                call_command("check_signer_config", stderr=stderr)
            assert exc_info.value.code == 1
            assert "NOT allowed" in stderr.getvalue()

    def test_warn_only_in_production_with_mock_exits_0(self):
        """--warn-only suppresses the exit in production mock scenario."""
        with patch(
            "apps.legalization.management.commands.check_signer_config.settings"
        ) as mock_settings:
            mock_settings.DJANGO_ENV = "production"
            mock_settings.SIGNATURE_PROVIDER = "mock"
            stdout = StringIO()
            stderr = StringIO()
            call_command("check_signer_config", "--warn-only", stdout=stdout, stderr=stderr)
            assert "WARNING" in stderr.getvalue()
            # Should NOT raise SystemExit.
