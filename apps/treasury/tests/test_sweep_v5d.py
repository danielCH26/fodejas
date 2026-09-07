"""Sweep tests for the 5-working-day Tesorería window (CHG-802 / CAP-010)."""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.treasury.models import DisbursementAuthorization
from apps.treasury.tasks import (
    _add_working_days,
    tesoreria_alert_v5d,
    tesoreria_sweep_v5d,
)


@pytest.mark.django_db(transaction=True)
class TestTesoreriaSweepV5D:
    """CAP-010: orders > 5 working days in ``ORDENADO`` state → VENCIDO."""

    def test_overdue_order_transitions_to_vencido(self, auth_factory):
        today = timezone.now().date()
        overdue_date = _add_working_days(today, -6)
        auth = auth_factory(
            status=DisbursementAuthorization.Status.ORDENADO,
            treasury_order_date=overdue_date,
        )
        transitioned = tesoreria_sweep_v5d()
        auth.refresh_from_db()
        assert transitioned == 1
        assert auth.status == DisbursementAuthorization.Status.VENCIDO

    def test_recent_order_not_transitioned(self, auth_factory):
        today = timezone.now().date()
        recent_date = _add_working_days(today, -4)
        auth = auth_factory(
            status=DisbursementAuthorization.Status.ORDENADO,
            treasury_order_date=recent_date,
        )
        transitioned = tesoreria_sweep_v5d()
        auth.refresh_from_db()
        assert transitioned == 0
        assert auth.status == DisbursementAuthorization.Status.ORDENADO

    def test_sweep_is_idempotent(self, auth_factory):
        """Running the sweep twice SHALL NOT double-transition."""
        today = timezone.now().date()
        overdue_date = _add_working_days(today, -6)
        auth = auth_factory(
            status=DisbursementAuthorization.Status.ORDENADO,
            treasury_order_date=overdue_date,
        )
        first = tesoreria_sweep_v5d()
        second = tesoreria_sweep_v5d()
        auth.refresh_from_db()
        assert first == 1
        assert second == 0
        assert auth.status == DisbursementAuthorization.Status.VENCIDO

    def test_paid_orders_are_not_swept(self, auth_factory):
        today = timezone.now().date()
        overdue_date = _add_working_days(today, -10)
        auth = auth_factory(
            status=DisbursementAuthorization.Status.PAGADO,
            treasury_order_date=overdue_date,
            paid_at=timezone.now(),
        )
        transitioned = tesoreria_sweep_v5d()
        auth.refresh_from_db()
        assert transitioned == 0
        assert auth.status == DisbursementAuthorization.Status.PAGADO


@pytest.mark.django_db(transaction=True)
class TestTesoreriaAlertV5D:
    """CAP-010 preventive alert at the 4-working-day mark."""

    def test_alert_marks_last_alerted_at(self, auth_factory):
        today = timezone.now().date()
        alert_date = _add_working_days(today, -4)
        auth = auth_factory(
            status=DisbursementAuthorization.Status.ORDENADO,
            treasury_order_date=alert_date,
        )
        alerted = tesoreria_alert_v5d()
        auth.refresh_from_db()
        assert alerted == 1
        assert auth.last_alerted_at is not None

    def test_alert_is_idempotent_within_same_day(self, auth_factory):
        today = timezone.now().date()
        alert_date = _add_working_days(today, -4)
        auth = auth_factory(
            status=DisbursementAuthorization.Status.ORDENADO,
            treasury_order_date=alert_date,
        )
        first = tesoreria_alert_v5d()
        second = tesoreria_alert_v5d()
        auth.refresh_from_db()
        assert first == 1
        assert second == 0
        assert auth.last_alerted_at is not None
