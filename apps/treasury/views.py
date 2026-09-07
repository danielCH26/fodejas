"""Views for the treasury app (CHG-802 / CAP-010).

Manual reconciliation flow per AGENTS.md §7: the platform orders
the payment, Tesorería executes outside the system and reports
back via this view by attaching ``payment_proof`` and confirming
the payment. No bank integration.
"""
from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from apps.audit.services import log_audit_event
from apps.treasury.models import DisbursementAuthorization
from apps.treasury.services import TreasuryService

logger = logging.getLogger(__name__)


class TreasuryReconciliationView(LoginRequiredMixin, View):
    """CBV for Tesorería to list and confirm ordered payments.

    GET: render the list of ``ORDENADO`` authorizations oldest-first.
    POST: confirm payment on a specific authorization (sets
    ``payment_proof``, transitions to ``PAGADO`` via
    ``TreasuryService.confirm_payment``).

    Access is restricted to users with the ``R-TESORERO`` role.
    Superusers / staff bypass.
    """

    def _user_can_reconcile(self, request):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.user_roles.filter(role__code="R-TESORERO").exists()

    def dispatch(self, request, *args, **kwargs):
        if not self._user_can_reconcile(request):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        authorizations = (
            DisbursementAuthorization.objects.filter(
                status=DisbursementAuthorization.Status.ORDENADO,
            )
            .order_by("treasury_order_date")
            .select_related("legalization_process")
        )
        context = {
            "authorizations": authorizations,
            "section": "treasury_reconciliation",
        }
        return render(
            request,
            "treasury/reconciliation.html",
            context,
        )

    def post(self, request, *args, **kwargs):
        auth_id = request.POST.get("auth_id")
        if not auth_id:
            messages.error(request, "Falta auth_id")
            return redirect(reverse("treasury:reconciliation"))

        auth = get_object_or_404(DisbursementAuthorization, id=auth_id)
        proof = request.FILES.get("payment_proof")
        try:
            # Pre-transition the row to RECIBIDO if it is still
            # in ORDENADO state (Tesorería acknowledges first).
            if auth.status == DisbursementAuthorization.Status.ORDENADO:
                TreasuryService.mark_as_received(auth.id)
            TreasuryService.confirm_payment(auth.id, payment_proof=proof)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect(reverse("treasury:reconciliation"))

        log_audit_event(
            actor=request.user,
            action="PAYMENT_CONFIRMED",
            entity="DisbursementAuthorization",
            entity_id=auth.id,
            changes={
                "amount": str(auth.amount),
                "treasury_order_number": auth.treasury_order_number,
            },
            module="treasury",
        )
        messages.success(request, "Pago confirmado correctamente.")
        return redirect(reverse("treasury:reconciliation"))
