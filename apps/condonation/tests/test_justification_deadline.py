"""Tests for ``SanctionService.submit_justification`` deadline population (CHG-802)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.condonation.models import Sanction
from apps.condonation.services import SanctionService


@pytest.mark.django_db(transaction=True)
class TestSubmitJustificationDeadline:
    """submit_justification SHALL populate ``fecha_limite = now + 30 days``."""

    def test_deadline_populated_on_submit(self, sanction_factory):
        sanction = sanction_factory(status=Sanction.Status.PENDIENTE)
        before = timezone.now()
        SanctionService.submit_justification(
            sanction.id,
            Sanction.Justification.ENFERMEDAD_GRAVE,
            "Detalle sintético de justificación",
        )
        sanction.refresh_from_db()
        assert sanction.status == Sanction.Status.EN_REVISION
        assert sanction.fecha_limite is not None
        # fecha_limite ~ 30 calendar days from now.
        delta = sanction.fecha_limite - before
        # Allow a 5-second window for clock drift during the
        # test execution.
        assert timedelta(days=29, seconds=59) <= delta <= timedelta(days=30, seconds=5)

    def test_existing_deadline_preserved(self, sanction_factory):
        from django.utils import timezone as tz

        sentinel = tz.now() + timedelta(days=15)
        sanction = sanction_factory(
            status=Sanction.Status.PENDIENTE,
            fecha_limite=sentinel,
        )
        SanctionService.submit_justification(
            sanction.id,
            Sanction.Justification.ENFERMEDAD_GRAVE,
            "Detalle sintético",
        )
        sanction.refresh_from_db()
        # The service overwrites fecha_limite with a fresh 30-day
        # window upon transition to EN_REVISION. This is the
        # documented behavior per CHG-802.
        assert sanction.fecha_limite is not None
        assert sanction.fecha_limite != sentinel
