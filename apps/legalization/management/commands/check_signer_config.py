"""Management command: check_signer_config (CHG-301).

Verifies that SIGNATURE_PROVIDER is appropriate for the current
DJANGO_ENV. Exits non-zero (sys.exit(1)) if:
  - In staging or production and SIGNATURE_PROVIDER == "mock"
    (a mock signature in production leaves "environment=development"
    metadata in every audit trail — proposal §Riesgos).

Usage:
    python manage.py check_signer_config
    python manage.py check_signer_config --warn-only   # development convenience

Exit codes:
    0  — provider is correct for this environment.
    1  — misconfiguration detected; fix SIGNATURE_PROVIDER and retry.
"""
from __future__ import annotations

import sys

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser


class Command(BaseCommand):
    """Check that SIGNATURE_PROVIDER is correctly set for the environment."""

    PRODUCTION_ENVS = frozenset({"staging", "production"})
    APPROVED_PRODUCTION = frozenset({"local"})  # local signer only in prod
    MOCK_ENV = "mock"

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--warn-only",
            action="store_true",
            help=(
                "Exit 0 even on misconfiguration; print a warning instead. "
                "Useful in development where you deliberately run mock."
            ),
        )

    def handle(self, **options) -> str | None:
        env = getattr(settings, "DJANGO_ENV", "development")
        provider = getattr(settings, "SIGNATURE_PROVIDER", self.MOCK_ENV)
        is_production = env in self.PRODUCTION_ENVS
        warn_only = bool(options["warn_only"])

        if is_production:
            if provider == self.MOCK_ENV:
                msg = (
                    f"[CHG-301] SIGNATURE_PROVIDER=mock is NOT allowed in "
                    f"environment {env!r}.  Use SIGNATURE_PROVIDER=local.  "
                    "Mock signatures leave environment=development metadata "
                    "in the audit trail, violating Decree 0372/2025 Art. 45 "
                    "integrity requirements."
                )
                if warn_only:
                    self.stderr.write(self.style.WARNING(f"WARNING: {msg}"))
                    return
                self.stderr.write(self.style.ERROR(f"ERROR: {msg}"))
                sys.exit(1)

            approved = self.APPROVED_PRODUCTION
            if provider not in approved:
                msg = (
                    f"[CHG-301] SIGNATURE_PROVIDER={provider!r} is not "
                    f"approved for environment {env!r}.  Approved: {sorted(approved)}."
                )
                if warn_only:
                    self.stderr.write(self.style.WARNING(f"WARNING: {msg}"))
                    return
                self.stderr.write(self.style.ERROR(f"ERROR: {msg}"))
                sys.exit(1)

            self.stdout.write(
                self.style.SUCCESS(
                    f"[CHG-301] SIGNATURE_PROVIDER={provider!r} "
                    f"is correct for environment {env!r}."
                )
            )
            return

        # Development / test environment.
        self.stdout.write(
            self.style.SUCCESS(
                f"[CHG-301] Environment {env!r} — "
                f"SIGNATURE_PROVIDER={provider!r}. "
                "Use --warn-only to suppress this output."
            )
        )
