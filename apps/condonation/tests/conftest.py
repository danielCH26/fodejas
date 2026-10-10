"""Shared pytest fixtures for condonation tests (CHG-802)."""

from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model


@pytest.fixture
def user_factory(db):
    CustomUser = get_user_model()
    counter = {"n": 0}

    def _make(**extra):
        counter["n"] += 1
        n = counter["n"]
        return CustomUser.objects.create_user(
            email=f"sanctions-{n}-{uuid.uuid4().hex[:6]}@example.test",
            documento=f"1234567{n:04d}",
            password="test-password-not-real",
            first_name="Synthetic",
            last_name="Condonación",
            **extra,
        )

    return _make


@pytest.fixture
def legalization_process(db, user_factory):
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
def termination_factory(db, legalization_process, user_factory):
    """Build a TerminationRequest in PENDIENTE state."""
    from apps.condonation.models import TerminationRequest

    def _make(**extra):
        user = user_factory()
        return TerminationRequest.objects.create(
            legalization_process=legalization_process,
            cause=TerminationRequest.Cause.INFORMACION_FALSA,
            requested_by=user,
            status=TerminationRequest.Status.PENDIENTE,
            **extra,
        )

    return _make


@pytest.fixture
def sanction_factory(db, termination_factory):
    from decimal import Decimal

    from apps.condonation.models import Sanction

    def _make(status=Sanction.Status.PENDIENTE, fecha_limite=None, **extra):
        termination = termination_factory()
        return Sanction.objects.create(
            termination=termination,
            base_amount=Decimal("1000000.00"),
            ipc_adjustment=Decimal("0.00"),
            total_amount=Decimal("1000000.00"),
            status=status,
            fecha_limite=fecha_limite,
            **extra,
        )

    return _make
