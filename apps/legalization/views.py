"""HTMX views for the legalization signature workflow (CHG-301, CAP-029)."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.template.loader import render_to_string
from django.views.generic import DetailView, TemplateView

from apps.accounts.permissions import has_any_role
from apps.legalization.models import LegalDocument, LegalizationProcess
from apps.legalization.services import sign_legal_document


class LegalizationListView(LoginRequiredMixin, TemplateView):
    """Lista de procesos de legalización del usuario actual."""

    template_name = "legalization/list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user = self.request.user

        if user.is_staff or user.is_superuser or has_any_role(user, ["R-JUNTA", "R-ADMIN"]):
            # Staff and JUNTA see all processes.
            ctx["processes"] = (
                LegalizationProcess.objects.select_related(
                    "beneficiary", "convocatoria"
                )
                .prefetch_related("documents")
                .order_by("-created_at")[:50]
            )
        else:
            ctx["processes"] = (
                LegalizationProcess.objects.filter(beneficiary=user)
                .select_related("convocatoria")
                .prefetch_related("documents")
                .order_by("-created_at")
            )
        return ctx


class LegalizationDetailView(LoginRequiredMixin, DetailView):
    """Detalle de un proceso de legalización con sus documentos."""

    model = LegalizationProcess
    template_name = "legalization/detail.html"
    context_object_name = "process"

    def get_queryset(self):
        user = self.request.user
        qs = LegalizationProcess.objects.select_related(
            "beneficiary", "convocatoria"
        ).prefetch_related("documents")
        if user.is_staff or user.is_superuser or has_any_role(user, ["R-JUNTA", "R-ADMIN"]):
            return qs
        return qs.filter(beneficiary=user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_sign_all"] = all(
            doc.status == LegalDocument.Status.PENDIENTE and bool(doc.pdf)
            for doc in ctx["process"].documents.all()
        )
        return ctx


class SignDocumentHTMXView(LoginRequiredMixin, DetailView):
    """HTMX-powered document signing view.

    Handles GET (show confirmation) and POST (execute signing).
    Returns HTML fragments (not JSON) so it works with htmx modal swap.
    """

    model = LegalDocument
    template_name = "legalization/partials/sign_form.html"
    context_object_name = "document"

    def get_queryset(self):
        user = self.request.user
        qs = LegalDocument.objects.select_related(
            "process", "process__beneficiary", "process__convocatoria"
        )
        if user.is_staff or user.is_superuser or has_any_role(user, ["R-JUNTA", "R-ADMIN"]):
            return qs
        return qs.filter(process__beneficiary=user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sign_error"] = self.request.session.pop("sign_error", None)
        return ctx

    def post(self, request, *args, **kwargs):
        """Sign the document via HTMX form submission."""
        self.object = self.get_object()
        document: LegalDocument = self.object

        if document.status != LegalDocument.Status.PENDIENTE:
            messages.error(
                request,
                f"El documento ya está en estado {document.status}.",
            )
            return self._render_swap("error")

        if not document.pdf:
            messages.error(request, "El documento no tiene PDF cargado.")
            return self._render_swap("error")

        try:
            sign_legal_document(document, actor=request.user)
            messages.success(
                request,
                f"Documento {document.get_document_type_display()} firmado exitosamente.",
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return self._render_swap("error")

        # Refresh the document row so the HTMX response reflects the new state.
        document.refresh_from_db()
        return self._render_swap("success")

    def _render_swap(self, state: str):
        """Render an htmx swap response.

        state:
            success — re-render the document row showing signed status.
            error   — re-render the form with error messages.
        """
        from django.http import HttpResponse

        if state == "success":
            # Replace the row with the updated signed document row.
            html = render_to_string(
                "legalization/partials/document_row.html",
                {"document": self.object, "process": self.object.process},
                request=self.request,
            )
        else:
            html = render_to_string(
                self.template_name,
                {"document": self.object, "sign_error": True},
                request=self.request,
            )
        return HttpResponse(
            html,
            headers={
                "HX-Reswap": "outerHTML",
                "HX-Retarget": f"#doc-row-{self.object.id}",
            },
        )


# Alias for URL naming consistency
sign_document_htmx = SignDocumentHTMXView.as_view()
