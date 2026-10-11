"""Shared pytest fixtures for treasury tests (CHG-802).

Uses synthetic data only — no PII per AGENTS.md §6 regla 1.
"""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def user_factory(db):
    """Synthetic user factory (no PII)."""
    CustomUser = get_user_model()
    counter = {"n": 0}

    def _make(
        email: str | None = None,
        documento: str | None = None,
        is_staff: bool = False,
        **extra,
    ):
        counter["n"] += 1
        n = counter["n"]
        return CustomUser.objects.create_user(
            email=email or f"treasury-{n}-{uuid.uuid4().hex[:6]}@example.test",
            documento=documento or f"1234567{n:04d}",
            password="test-password-not-real",
            first_name="Synthetic",
            last_name="Tesorería",
            is_staff=is_staff,
            **extra,
        )

    return _make


@pytest.fixture
def legalization_process(db, user_factory):
    """Build a real ``LegalizationProcess`` (needed for FK from disbursement)."""
    from apps.convocatories.models import Convocatory
    from apps.legalization.models import LegalizationProcess

    beneficiary = user_factory()
    convocatory = Convocatory.objects.create(
        nombre=f"Convocatoria Sintética {uuid.uuid4().hex[:6]}",
        codigo=f"syn-{uuid.uuid4().hex[:8]}",
        periodo="2099-1",
    )
    return LegalizationProcess.objects.create(
        beneficiary=beneficiary,
        convocatoria=convocatory,
        status="LEGALIZADO",
    )


@pytest.fixture
def auth_factory(db, legalization_process):
    """Factory for synthetic ``DisbursementAuthorization`` rows."""
    from apps.treasury.models import DisbursementAuthorization

    def _make(status="PENDIENTE", treasury_order_date=None, **extra):
        return DisbursementAuthorization.objects.create(
            legalization_process=legalization_process,
            amount="1000000.00",
            status=status,
            treasury_order_date=treasury_order_date,
            **extra,
        )

    return _make


@pytest.fixture
def tesorero_role(db):
    from apps.accounts.models import Role

    role, _ = Role.objects.get_or_create(
        code="R-TESOR",
        defaults={
            "name": "Tesorero",
            "type": "interno",
            "description": "Rol interno de Tesorería (sintético, seeded as R-TESOR).",
        },
    )
    return role
