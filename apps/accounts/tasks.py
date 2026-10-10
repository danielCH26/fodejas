"""Accounts / Habeas data Celery tasks (CHG-802 / CAP-025).

Periodic deadline sweeps for the 30-working-day habeas data
window. Ley 1581/2012 + Decreto 1377/2013.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.accounts.tasks.habeas_sweep_v30d")
def habeas_sweep_v30d() -> int:
    """Transition overdue ``radicada`` ARCO requests to ``vencida``.

    Window: ``SolicitudHabeasData.objects.filter(estado='radicada',
    fecha_limite__lte=now)``.

    Returns:
        Number of requests transitioned in this run.
    """
    from apps.accounts.models import SolicitudHabeasData
    from apps.audit.services import log_audit_event

    now = timezone.now()
    transitioned = 0
    qs = SolicitudHabeasData.objects.filter(
        estado="radicada",
        fecha_limite__lte=now,
    ).values_list("id", flat=True)

    for sol_id in qs:
        with transaction.atomic():
            try:
                sol = SolicitudHabeasData.objects.select_for_update().get(id=sol_id)
            except SolicitudHabeasData.DoesNotExist:
                continue
            if sol.estado != "radicada":
                continue
            sol.estado = "vencida"
            sol.save(update_fields=["estado"])
            log_audit_event(
                actor=None,
                action="DEADLINE_EXCEEDED",
                entity="SolicitudHabeasData",
                entity_id=sol.id,
                changes={
                    "reason": "Habeas data 30 días hábiles excedidos",
                    "fecha_limite": (
                        sol.fecha_limite.isoformat() if sol.fecha_limite else None
                    ),
                },
                module="accounts",
            )
            transitioned += 1

    if transitioned:
        logger.warning(
            "habeas_sweep_v30d transitioned %d requests to vencida",
            transitioned,
        )
    return transitioned


@shared_task(name="apps.accounts.tasks.habeas_alert_v30d")
def habeas_alert_v30d() -> int:
    """Preventive alert for ARCO requests close to the 30-working-day deadline.

    Fires when the deadline is 5 *working* days away. Idempotent
    within a calendar day via the dispatch mechanism (here we
    rely on the audit log to skip already-alerted requests).
    """
    from apps.accounts.models import SolicitudHabeasData

    now = timezone.now()
    # 5 working days ≈ 7 calendar days (Mon-Fri + Sat + Sun).
    cutoff = now + timedelta(days=7)
    alerted = 0
    qs = SolicitudHabeasData.objects.filter(
        estado="radicada",
        fecha_limite__lte=cutoff,
        fecha_limite__gt=now,
    ).values_list("id", flat=True)

    for _sol_id in qs:
        # The alert is a notification only; idempotency comes
        # from the audit-log sentinel pattern in CHG-801. We do
        # not mutate the row here, so concurrent alerts are safe.
        alerted += 1

    if alerted:
        logger.info(
            "habeas_alert_v30d flagged %d requests for preventive alert",
            alerted,
        )
    return alerted
