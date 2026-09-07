"""Shared pytest fixtures for the audit app test suite.

Uses synthetic data only (no PII) per AGENTS.md §6 regla 1.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def user_factory(db):
    """Return a callable that creates synthetic ``CustomUser`` instances.

    Synthetic identifiers (e.g. ``1234567890``) are used instead of
    real documents per AGENTS.md §6 regla 1.
    """
    CustomUser = get_user_model()
    counter = {"n": 0}

    def _make(
        email: str | None = None,
        documento: str | None = None,
        is_staff: bool = False,
        is_superuser: bool = False,
        **extra,
    ):
        counter["n"] += 1
        n = counter["n"]
        return CustomUser.objects.create_user(
            email=email or f"synthetic-{n}-{uuid.uuid4().hex[:6]}@example.test",
            documento=documento or f"1234567{n:04d}",
            password="test-password-not-real",
            first_name="Aspirante",
            last_name="Ejemplo",
            is_staff=is_staff,
            is_superuser=is_superuser,
            **extra,
        )

    return _make


@pytest.fixture
def admin_user(user_factory):
    """Synthetic superuser."""
    user = user_factory(is_staff=True, is_superuser=True)
    return user


@pytest.fixture
def auditor_role(db):
    """Create the ``R-ADMIN`` role used by ``IsAuditViewer``."""
    from apps.accounts.models import Role

    role, _ = Role.objects.get_or_create(
        code="R-ADMIN",
        defaults={
            "name": "Administrador",
            "type": "interno",
            "description": "Rol administrativo sintético para tests.",
        },
    )
    return role


@pytest.fixture
def control_role(db):
    """Create the ``R-CONTROL`` role used by ``IsAuditViewer``."""
    from apps.accounts.models import Role

    role, _ = Role.objects.get_or_create(
        code="R-CONTROL",
        defaults={
            "name": "Control",
            "type": "interno",
            "description": "Rol de control sintético para tests.",
        },
    )
    return role


@pytest.fixture
def aspirante_role(db):
    """Create the ``R-ASPIRANTE`` role used to assert denial."""
    from apps.accounts.models import Role

    role, _ = Role.objects.get_or_create(
        code="R-ASPIRANTE",
        defaults={
            "name": "Aspirante",
            "type": "externo",
            "description": "Rol externo sintético para tests.",
        },
    )
    return role


@pytest.fixture
def admin_user_with_role(user_factory, auditor_role):
    """A user that has the ``R-ADMIN`` role assigned."""
    from apps.accounts.models import UserRole

    user = user_factory()
    UserRole.objects.create(user=user, role=auditor_role)
    return user


@pytest.fixture
def aspirante_user_with_role(user_factory, aspirante_role):
    """A user that has the ``R-ASPIRANTE`` role assigned."""
    from apps.accounts.models import UserRole

    user = user_factory()
    UserRole.objects.create(user=user, role=aspirante_role)
    return user