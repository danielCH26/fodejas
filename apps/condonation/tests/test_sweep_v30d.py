"""Sweep tests for the 30-calendar-day exoneration window (CHG-802 / CAP-016)."""
from __future__ import annotations

import pytest
from django.utils import timezone

from apps.condonation.models import Sanction
from apps.condonation.tasks import (
    exoneracion_alert_v30d,
    exoneracion_sweep_v30d,
)


@pytest.mark.django_db(transaction=True)
class TestExoneracionSweepV30D:
    """CAP-016: EN_REVISION sanctions past fecha_limite → VENCIDO."""

    def test_overdue_sanction_transitions_to_vencido(self, sanction_factory):
        sanction = sanction_factory(
            status=Sanction.Status.EN_REVISION,
            fecha_limite=timezone.now(),
        )
        transitioned = exoneracion_sweep_v30d()
        sanction.refresh_from_db()
        assert transitioned == 1
        assert sanction.status == Sanction.Status.VENCIDO

    def test_future_deadline_not_transitioned(self, sanction_factory):
        from datetime import timedelta

        sanction = sanction_factory(
            status=Sanction.Status.EN_REVISION,
            fecha_limite=timezone.now() + timedelta(days=5),
        )
        transitioned = exoneracion_sweep_v30d()
        sanction.refresh_from_db()
        assert transitioned == 0
        assert sanction.status == Sanction.Status.EN_REVISION

    def test_sweep_is_idempotent(self, sanction_factory):
        sanction = sanction_factory(
            status=Sanction.Status.EN_REVISION,
            fecha_limite=timezone.now(),
        )
        first = exoneracion_sweep_v30d()
        second = exoneracion_sweep_v30d()
        sanction.refresh_from_db()
        assert first == 1
        assert second == 0
        assert sanction.status == Sanction.Status.VENCIDO


@pytest.mark.django_db(transaction=True)
class TestExoneracionAlertV30D:
    """Preventive alert at the 5-day mark (CHG-802 / CAP-016)."""

    def test_alert_flags_close_to_deadline(self, sanction_factory):
        from datetime import timedelta

        sanction = sanction_factory(
            status=Sanction.Status.EN_REVISION,
            fecha_limite=timezone.now() + timedelta(days=3),
        )
        alerted = exoneracion_alert_v30d()
        assert alerted == 1
        sanction.refresh_from_db()
        assert sanction.last_alerted_at is not None

    def test_alert_does_not_fire_for_far_deadlines(self, sanction_factory):
        from datetime import timedelta

        sanction_factory(
            status=Sanction.Status.EN_REVISION,
            fecha_limite=timezone.now() + timedelta(days=20),
        )
        alerted = exoneracion_alert_v30d()
        assert alerted == 0

    def test_alert_is_idempotent_within_same_day(self, sanction_factory):
        from datetime import timedelta

        sanction = sanction_factory(
            status=Sanction.Status.EN_REVISION,
            fecha_limite=timezone.now() + timedelta(days=3),
        )
        first = exoneracion_alert_v30d()
        second = exoneracion_alert_v30d()
        sanction.refresh_from_db()
        assert first == 1
        assert second == 0
