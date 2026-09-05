"""Views for treasury app."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.views.generic import DetailView, ListView, TemplateView, View

from apps.treasury.models import DisbursementAuthorization
from apps.treasury.services import TreasuryService


class DisbursementListView(LoginRequiredMixin, ListView):
    """List all disbursement authorizations."""

    model = DisbursementAuthorization
    template_name = "treasury/list.html"
    context_object_name = "disbursements"

    def get_queryset(self):
        queryset = DisbursementAuthorization.objects.select_related(
            "legalization_process__beneficiary",
            "legalization_process__convocatoria",
        ).order_by("-created_at")

        # Filter by status
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = DisbursementAuthorization.Status.choices
        return context


class DisbursementDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a disbursement authorization."""

    model = DisbursementAuthorization
    template_name = "treasury/detail.html"
    context_object_name = "disbursement"

    def get_queryset(self):
        return DisbursementAuthorization.objects.select_related(
            "legalization_process__beneficiary",
            "legalization_process__convocatoria",
        )


class DisbursementAuthorizeView(LoginRequiredMixin, View):
    """Authorize a disbursement (President or Secretary)."""

    def post(self, request, pk, role):
        disbursement = get_object_or_404(DisbursementAuthorization, pk=pk)

        try:
            TreasuryService.authorize(disbursement, request.user, role)
            messages.success(request, f"Desembolso autorizado como {role}.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect("treasury:detail", pk=disbursement.pk)


class TreasuryDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for treasury staff."""

    template_name = "treasury/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Stats
        context["total_disbursements"] = DisbursementAuthorization.objects.count()
        context["pending_count"] = DisbursementAuthorization.objects.filter(
            status=DisbursementAuthorization.Status.PENDIENTE
        ).count()
        context["authorized_count"] = DisbursementAuthorization.objects.filter(
            status=DisbursementAuthorization.Status.AUTORIZADO
        ).count()
        context["paid_count"] = DisbursementAuthorization.objects.filter(
            status=DisbursementAuthorization.Status.PAGADO
        ).count()

        # Recent
        context["recent_disbursements"] = DisbursementAuthorization.objects.select_related(
            "legalization_process__beneficiary"
        ).order_by("-created_at")[:10]

        return context


class TreasuryConfirmPaymentView(LoginRequiredMixin, View):
    """Confirm payment and upload proof."""

    def post(self, request, pk):
        disbursement = get_object_or_404(DisbursementAuthorization, pk=pk)

        # Get uploaded file
        payment_proof = request.FILES.get("payment_proof")
        if not payment_proof:
            messages.error(request, "Debe subir el comprobante de pago.")
            return redirect("treasury:detail", pk=disbursement.pk)

        try:
            TreasuryService.confirm_payment(disbursement, payment_proof, request.user)
            messages.success(request, "Pago confirmado exitosamente.")
        except Exception as e:
            messages.error(request, f"Error: {e}")

        return redirect("treasury:detail", pk=disbursement.pk)
