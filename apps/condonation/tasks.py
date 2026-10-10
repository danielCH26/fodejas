"""Condonation Celery tasks (CHG-802 / CAP-016).

Periodic deadline sweeps for the 30-calendar-day exoneration
window. Decreto 0372/2025 Art. 17.
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name="apps.condonation.tasks.exoneracion_sweep_v30d")
def exoneracion_sweep_v30d() -> int:
    """Transition overdue ``EN_REVISION`` sanctions to ``VENCIDO``.

    Window: ``Sanction.objects.filter(status='EN_REVISION',
    fecha_limite__lte=now)``. Rows already in ``VENCIDO`` are
    skipped (idempotent across re-runs).

    Returns:
        Number of sanctions transitioned in this run.
    """
    from apps.audit.services import log_audit_event
    from apps.condonation.models import Sanction
    from apps.condonation.services import SanctionService

    now = timezone.now()
    transitioned = 0
    qs = Sanction.objects.filter(
        status=Sanction.Status.EN_REVISION,
        fecha_limite__lte=now,
    ).values_list("id", flat=True)

    for sanction_id in qs:
        with transaction.atomic():
            sanction = SanctionService.mark_as_expired(sanction_id)
            if sanction is None or sanction.status != Sanction.Status.VENCIDO:
                continue
            log_audit_event(
                actor=None,
                action="DEADLINE_EXCEEDED",
                entity="Sanction",
                entity_id=sanction.id,
                changes={
                    "reason": "Exoneración 30 días calendario excedidos",
                    "fecha_limite": (
                        sanction.fecha_limite.isoformat() if sanction.fecha_limite else None
                    ),
                },
                module="condonation",
            )
            transitioned += 1

    if transitioned:
        logger.warning(
            "exoneracion_sweep_v30d transitioned %d sanctions to VENCIDO",
            transitioned,
        )
    return transitioned


@shared_task(name="apps.condonation.tasks.exoneracion_alert_v30d")
def exoneracion_alert_v30d() -> int:
    """Preventive alert for exonerations close to the 30-day deadline.

    Fires when the deadline is 5 calendar days away. Idempotent
    within a calendar day via the ``last_alerted_at`` column on
    the row.
    """
    from datetime import timedelta

    from apps.condonation.models import Sanction

    now = timezone.now()
    cutoff = now + timedelta(days=5)
    alerted = 0
    qs = Sanction.objects.filter(
        status=Sanction.Status.EN_REVISION,
        fecha_limite__lte=cutoff,
        fecha_limite__gt=now,
    ).values_list("id", flat=True)

    for sanction_id in qs:
        with transaction.atomic():
            try:
                sanction = Sanction.objects.select_for_update().get(id=sanction_id)
            except Sanction.DoesNotExist:
                continue
            if sanction.last_alerted_at and sanction.last_alerted_at.date() == now.date():
                continue
            if sanction.status != Sanction.Status.EN_REVISION:
                continue
            sanction.last_alerted_at = now
            sanction.save(update_fields=["last_alerted_at", "updated_at"])
            alerted += 1

    if alerted:
        logger.info(
            "exoneracion_alert_v30d flagged %d sanctions for preventive alert",
            alerted,
        )
    return alerted
