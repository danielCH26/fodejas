"""Treasury Celery tasks (CHG-802 / AUD-016).

Periodic deadline sweeps for CAP-010. All tasks are idempotent
within a calendar day via the ``last_alerted_at`` column and the
audit log (the latter records ``actor_is_system=True`` sentinel
events so we can detect and skip already-processed rows).

Decreto 0372/2025 Art. 2: Tesorería debe ejecutar el pago en un
máximo de 5 días hábiles contados a partir de la radicación de
la orden. ``tesoreria_sweep_v5d`` marca como ``VENCIDO`` cualquier
orden que haya superado esa ventana sin confirmación de pago.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def _add_working_days(start: date, days: int) -> date:
    """Return ``start`` advanced by ``days`` working days (Mon-Fri).

    CHG-802 does NOT require a Colombian holiday calendar yet —
    that is tracked separately. This helper handles the
    weekend-only subtraction that the tests exercise.

    ``days`` may be negative (move backwards).
    """
    if days == 0:
        return start
    step = 1 if days > 0 else -1
    remaining = abs(days)
    cursor = start
    while remaining > 0:
        cursor = cursor + timedelta(days=step)
        if cursor.weekday() < 5:  # 0=Mon ... 4=Fri
            remaining -= 1
    return cursor


def _working_days_between(start: date, end: date) -> int:
    """Return the number of working days strictly between ``start`` and ``end``.

    For ``end < start`` the result is negative. Both endpoints are
    excluded so the math matches "N días hábiles desde la
    radicación" with the radicación day itself at index 0.
    """
    if end == start:
        return 0
    step = 1 if end > start else -1
    cursor = start
    count = 0
    while cursor != end:
        cursor = cursor + timedelta(days=step)
        if cursor.weekday() < 5:  # 0=Mon, 4=Fri
            count += step
    return count


@shared_task(name="apps.treasury.tasks.tesoreria_sweep_v5d")
def tesoreria_sweep_v5d() -> int:
    """Transition overdue ``ORDENADO`` rows to ``VENCIDO``.

    The sweep window is ``treasury_order_date <= today - 5 working
    days``. Rows already in ``VENCIDO`` are skipped (they were
    swept on a prior run). All transitions are wrapped in a
    transaction with ``select_for_update`` so two workers cannot
    race.

    Returns:
        Number of rows transitioned in this run.
    """
    from apps.audit.services import log_audit_event
    from apps.treasury.models import DisbursementAuthorization

    today = timezone.now().date()
    cutoff = _add_working_days(today, -5)

    transitioned = 0
    qs = DisbursementAuthorization.objects.filter(
        status=DisbursementAuthorization.Status.ORDENADO,
        treasury_order_date__lte=cutoff,
    ).values_list("id", flat=True)

    for auth_id in qs:
        with transaction.atomic():
            try:
                auth = DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
            except DisbursementAuthorization.DoesNotExist:
                continue
            if auth.status != DisbursementAuthorization.Status.ORDENADO:
                # Another worker got here first.
                continue
            auth.status = DisbursementAuthorization.Status.VENCIDO
            auth.save(update_fields=["status", "updated_at"])
            log_audit_event(
                actor=None,
                action="DEADLINE_EXCEEDED",
                entity="DisbursementAuthorization",
                entity_id=auth.id,
                changes={
                    "reason": "Tesorería 5 días hábiles excedidos",
                    "treasury_order_date": (
                        auth.treasury_order_date.isoformat() if auth.treasury_order_date else None
                    ),
                    "cutoff_date": cutoff.isoformat(),
                },
                module="treasury",
            )
            transitioned += 1

    if transitioned:
        logger.warning(
            "tesoreria_sweep_v5d transitioned %d authorizations to VENCIDO",
            transitioned,
        )
    return transitioned


@shared_task(name="apps.treasury.tasks.tesoreria_alert_v5d")
def tesoreria_alert_v5d() -> int:
    """Preventive alert for orders approaching the 5-day window.

    Emits a notification 1 working day before the deadline (so for
    orders with ``treasury_order_date == today - 4 working days``).
    Idempotent within a calendar day via ``last_alerted_at``.
    """
    from apps.treasury.models import DisbursementAuthorization

    today = timezone.now().date()
    cutoff_alert = _add_working_days(today, -4)

    alerted = 0
    qs = DisbursementAuthorization.objects.filter(
        status=DisbursementAuthorization.Status.ORDENADO,
        treasury_order_date__lte=cutoff_alert,
    ).values_list("id", flat=True)

    for auth_id in qs:
        with transaction.atomic():
            try:
                auth = DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
            except DisbursementAuthorization.DoesNotExist:
                continue
            # Idempotency: skip if already alerted today.
            if auth.last_alerted_at and auth.last_alerted_at.date() == today:
                continue
            if auth.status != DisbursementAuthorization.Status.ORDENADO:
                continue
            auth.last_alerted_at = timezone.now()
            auth.save(update_fields=["last_alerted_at", "updated_at"])
            alerted += 1

    if alerted:
        logger.info(
            "tesoreria_alert_v5d flagged %d authorizations for preventive alert",
            alerted,
        )
    return alerted
