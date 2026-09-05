"""Views for legalization app."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, TemplateView, View

from apps.accounts.permissions import IsAdminRole
from apps.legalization.models import LegalDocument, LegalizationProcess
from apps.legalization.services import LegalizationService


class LegalizationListView(LoginRequiredMixin, ListView):
    """List all legalization processes."""

    model = LegalizationProcess
    template_name = "legalization/list.html"
    context_object_name = "processes"

    def get_queryset(self):
        queryset = LegalizationProcess.objects.select_related(
            "beneficiary", "convocatoria"
        ).order_by("-created_at")

        # Filter by status
        status = self.request.GET.get("status")
        if status:
            queryset = queryset.filter(status=status)

        # Filter by convocatoria
        conv = self.request.GET.get("convocatoria")
        if conv:
            queryset = queryset.filter(convocatoria_id=conv)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_choices"] = LegalizationProcess.Status.choices
        return context


class LegalizationDetailView(LoginRequiredMixin, DetailView):
    """Detail view for a legalization process."""

    model = LegalizationProcess
    template_name = "legalization/detail.html"
    context_object_name = "process"

    def get_queryset(self):
        return LegalizationProcess.objects.select_related(
            "beneficiary", "convocatoria"
        ).prefetch_related("documents")


class LegalDocumentSignView(LoginRequiredMixin, View):
    """View to sign a legal document."""

    def post(self, request, pk):
        document = get_object_or_404(LegalDocument, pk=pk)

        if document.status != LegalDocument.Status.PENDIENTE:
            messages.error(request, "El documento no está en estado pendiente.")
            return redirect("legalization:detail", pk=document.process.pk)

        try:
            # Sign the document
            LegalizationService.sign_document(document, actor_id=request.user.id)
            messages.success(request, "Documento firmado exitosamente.")
        except Exception as e:
            messages.error(request, f"Error al firmar: {e}")

        return redirect("legalization:detail", pk=document.process.pk)


class LegalizationDashboardView(LoginRequiredMixin, TemplateView):
    """Dashboard for legal staff (R-JUNTA)."""

    template_name = "legalization/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Stats
        context["total_processes"] = LegalizationProcess.objects.count()
        context["pending_count"] = LegalizationProcess.objects.filter(
            status=LegalizationProcess.Status.PENDIENTE
        ).count()
        context["signed_count"] = LegalizationProcess.objects.filter(
            status=LegalizationProcess.Status.FIRMADO
        ).count()
        context["legalized_count"] = LegalizationProcess.objects.filter(
            status=LegalizationProcess.Status.LEGALIZADO
        ).count()

        # Recent processes
        context["recent_processes"] = LegalizationProcess.objects.select_related(
            "beneficiary", "convocatoria"
        ).order_by("-created_at")[:10]

        return context
