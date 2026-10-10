"""Views for the treasury app (CHG-802 / CHG-303 / CAP-010).

Manual reconciliation flow per AGENTS.md §7: the platform orders
the payment, Tesorería executes outside the system and reports
back via this view by attaching ``payment_proof`` and confirming
the payment. No bank integration.

CHG-303 Batch B: disbursement authorization list, detail, and
HTMX authorize-action views for the doble-firma workflow
(president R-JUNTA + secretary R-COORDINADOR).
"""
from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View

from apps.accounts.permissions import has_any_role
from apps.audit.services import log_audit_event
from apps.legalization.models import LegalDocument
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


# ---------------------------------------------------------------------------
# CHG-303 Batch B — Disbursement authorization views
# ---------------------------------------------------------------------------

# Roles that can view and sign disbursement authorizations.
AUTHORIZATION_ROLES = ("R-JUNTA", "R-COORDINADOR")
SIGNABLE_ROLES = ("R-JUNTA", "R-COORDINADOR")


class DisbursementAuthorizationListView(LoginRequiredMixin, View):
    """Lista de autorizaciones de desembolso pendientes/autorizadas.

    Visible para R-JUNTA y R-COORDINADOR (doble firma).
    Muestra solo PENDIENTE y AUTORIZADO — las demás etapas
    (ORDENADO, RECIBIDO, PAGADO) se gestionan en conciliación.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('accounts:login')}?next={request.path}")
        if (
            request.user.is_superuser
            or request.user.is_staff
            or has_any_role(request.user, AUTHORIZATION_ROLES)
        ):
            return super().dispatch(request, *args, **kwargs)
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    def get(self, request, *args, **kwargs):
        authorizations = (
            DisbursementAuthorization.objects
            .filter(
                status__in=[
                    DisbursementAuthorization.Status.PENDIENTE,
                    DisbursementAuthorization.Status.AUTORIZADO,
                ]
            )
            .select_related("legalization_process__convocatoria")
            .order_by("-created_at")
        )
        context = {
            "authorizations": authorizations,
            "section": "treasury_disbursement",
        }
        return render(
            request,
            "treasury/disbursement_list.html",
            context,
        )


class DisbursementAuthorizationDetailView(LoginRequiredMixin, View):
    """Detalle de una autorización de desembolso.

    Muestra:
      - Estado de doble firma (quién firmó, rol, faltante)
      - Proceso de legalización relacionado
      - 4 adjuntos normativos requeridos con estado
      - Info de orden de tesorería (si fue enviada)
      - Comprobante de pago (si ya se concilió)
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{reverse('accounts:login')}?next={request.path}")
        if (
            request.user.is_superuser
            or request.user.is_staff
            or has_any_role(request.user, AUTHORIZATION_ROLES)
        ):
            return super().dispatch(request, *args, **kwargs)
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied

    def get(self, request, *args, **kwargs):
        auth = get_object_or_404(
            DisbursementAuthorization.objects.select_related(
                "legalization_process__convocatoria",
                "authorized_by_president",
                "authorized_by_secretary",
            ),
            pk=kwargs["pk"],
        )
        process = auth.legalization_process

        # Determine which role the current user can sign (if any).
        user_role_codes = set(
            request.user.user_roles.values_list("role__code", flat=True)
        )
        signing_roles = user_role_codes & set(SIGNABLE_ROLES)
        can_sign = False
        missing_role = None
        if auth.status == DisbursementAuthorization.Status.PENDIENTE:
            if "R-JUNTA" in signing_roles and not auth.authorized_by_president:
                can_sign = True
                missing_role = "president"
            elif "R-COORDINADOR" in signing_roles and not auth.authorized_by_secretary:
                can_sign = True
                missing_role = "secretary"

        # The 4 required normative attachment types.
        required_attachment_types = list(TreasuryService.REQUIRED_ATTACHMENT_TYPES)

        context = {
            "authorization": auth,
            "process": process,
            "can_sign": can_sign,
            "missing_role": missing_role,
            "required_attachment_types": required_attachment_types,
            "section": "treasury_disbursement",
        }
        return render(
            request,
            "treasury/disbursement_detail.html",
            context,
        )


class AuthorizeDisbursementHTMXView(LoginRequiredMixin, View):
    """HTMX view to sign (authorize) a disbursement.

    GET  — renders the authorize confirmation form (partial).
    POST — calls TreasuryService.authorize with current user + role;
           surfaces validation errors inline (self-signing,
           duplicate-role, wrong status).

    Only R-JUNTA (president) and R-COORDINADOR (secretary) can sign.
    The two distinct signatures complete the authorization.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        if not (
            request.user.is_superuser
            or request.user.is_staff
            or has_any_role(request.user, SIGNABLE_ROLES)
        ):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        auth = get_object_or_404(
            DisbursementAuthorization.objects.select_related(
                "legalization_process"
            ),
            pk=kwargs["pk"],
        )
        # Determine which role the user can sign as.
        user_role_codes = set(
            request.user.user_roles.values_list("role__code", flat=True)
        )
        can_sign_as = []
        if "R-JUNTA" in user_role_codes and not auth.authorized_by_president:
            can_sign_as.append("president")
        if "R-COORDINADOR" in user_role_codes and not auth.authorized_by_secretary:
            can_sign_as.append("secretary")

        return render(
            request,
            "treasury/partials/authorize_form.html",
            {
                "authorization": auth,
                "can_sign_as": can_sign_as,
                "section": "treasury_disbursement",
            },
        )

    def post(self, request, *args, **kwargs):
        auth = get_object_or_404(
            DisbursementAuthorization,
            pk=kwargs["pk"],
        )
        role = request.POST.get("role", "").strip().lower()
        if role not in ("president", "secretary"):
            return HttpResponse(
                '<div class="alert alert-danger">Rol inválido. Use president o secretary.</div>',
                status=400,
                headers={"HX-Reswap": "outerHTML"},
            )
        try:
            auth = TreasuryService.authorize(
                auth.id, user=request.user, role=role
            )
            messages.success(
                request,
                f"Firma de {role} registrada exitosamente."
                if not auth.is_fully_authorized
                else "¡Desembolso autorizado! Ambas firmas completadas.",
            )
        except ValueError as exc:
            msg = str(exc)
            messages.error(request, msg)
            return self._render_error(auth, msg)

        # Refresh so the partial reflects the updated state.
        auth.refresh_from_db()
        html = render_to_string(
            "treasury/partials/signature_status.html",
            {"authorization": auth, "process": auth.legalization_process},
            request=request,
        )
        return HttpResponse(
            html,
            headers={
                "HX-Reswap": "outerHTML",
                "HX-Retarget": "#signature-status",
            },
        )

    def _render_error(self, auth, error_msg):
        from django.http import HttpResponse

        html = render_to_string(
            "treasury/partials/authorize_error.html",
            {"authorization": auth, "error": error_msg},
            request=self.request,
        )
        return HttpResponse(
            html,
            status=400,
            headers={"HX-Reswap": "outerHTML", "HX-Retarget": "#authorize-errors"},
        )
