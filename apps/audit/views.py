"""Views for audit app."""

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions
from rest_framework.response import Response

from apps.accounts.permissions import IsAuditViewer

from .models import AuditEvent
from .serializers import AuditChainVerifySerializer, AuditEventSerializer
from .services import verify_chain


class AuditEventListView(generics.ListAPIView):
    """List audit events with filters.

    Permission tightened in CHG-801 (AUD-015): only users with
    R-ADMIN or R-CONTROL (or superuser / staff) may read the audit
    log. The previous ``IsAuthenticated`` only was too permissive.
    """

    queryset = AuditEvent.objects.all()
    serializer_class = AuditEventSerializer
    permission_classes = [IsAuditViewer]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = {
        "actor": ["exact"],
        "action": ["exact"],
        "entity": ["exact"],
        "entity_id": ["exact"],
        "module": ["exact"],
        "timestamp": ["gte", "lte", "exact"],
    }

    search_fields = ["entity", "module"]
    ordering_fields = ["timestamp", "action", "entity"]
    ordering = ["-timestamp"]


class AuditEventDetailView(generics.RetrieveAPIView):
    """Retrieve a single audit event.

    Same permission tightening as ``AuditEventListView`` (CHG-801 /
    AUD-015).
    """

    queryset = AuditEvent.objects.all()
    serializer_class = AuditEventSerializer
    permission_classes = [IsAuditViewer]
    lookup_field = "id"


class AuditChainVerifyView(generics.RetrieveAPIView):
    """Verify the integrity of the audit chain.

    Verification triggers a chain-wide scan and exposes integrity
    metadata, so it stays restricted to admin users only.
    """

    permission_classes = [permissions.IsAdminUser]
    serializer_class = AuditChainVerifySerializer

    def retrieve(self, request, *args, **kwargs):
        """Verify the audit chain."""
        result = verify_chain()
        return Response(result)


# === HTML Views for User Interface ===

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.urls import reverse_lazy
from django.views.generic import DetailView, TemplateView

from apps.audit import selectors


class AuditPermissionMixin:
    """Mixin that checks audit view permissions."""

    def get_permissions(self):
        return [IsAuditViewer()]

    def get_login_url(self):
        return reverse_lazy("accounts:login")


class BaseAuditView(LoginRequiredMixin, AuditPermissionMixin, TemplateView):
    """Base view for audit pages."""

    login_url = reverse_lazy("accounts:login")

    def get(self, request, *args, **kwargs):
        # Check permission manually to show custom message
        if not self.has_permission(request, self):
            messages.error(request, "No tienes permiso para acceder a la auditoría.")
            from django.shortcuts import redirect

            return redirect("dashboard")
        return super().get(request, *args, **kwargs)

    def has_permission(self, request, view):
        """Check if user has audit viewer permission."""
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.user_roles.filter(role__code__in=["R-ADMIN", "R-CONTROL"]).exists()


class AuditDashboardView(BaseAuditView):
    """Dashboard with audit event listing and filters."""

    template_name = "audit/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get filter parameters
        actor = self.request.GET.get("actor")
        action = self.request.GET.get("action")
        entity = self.request.GET.get("entity")
        module = self.request.GET.get("module")
        timestamp_from = self.request.GET.get("timestamp_from")
        timestamp_to = self.request.GET.get("timestamp_to")
        search = self.request.GET.get("search")

        # Get filtered queryset
        events = selectors.get_audit_events(
            actor=actor,
            action=action,
            entity=entity,
            module=module,
            timestamp_from=timestamp_from,
            timestamp_to=timestamp_to,
            search=search,
        )

        # Paginate
        paginator = Paginator(events, 50)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context.update(
            {
                "page_obj": page_obj,
                "events": page_obj.object_list,
                "filters": {
                    "actor": actor or "",
                    "action": action or "",
                    "entity": entity or "",
                    "module": module or "",
                    "timestamp_from": timestamp_from or "",
                    "timestamp_to": timestamp_to or "",
                    "search": search or "",
                },
                "action_choices": AuditEvent.ACTION_CHOICES,
                "entities": selectors.get_audit_entities(),
                "modules": selectors.get_audit_modules(),
                "stats": selectors.get_audit_stats(),
            }
        )

        return context


class AuditEventHtmlDetailView(LoginRequiredMixin, DetailView):
    """HTML detail view for a single audit event.

    Renamed from ``AuditEventDetailView`` — it shadowed the DRF
    view of the same name, so ``apps/audit/urls.py`` was silently
    serving this HTML view (no ``IsAuditViewer``) on the API route.
    """

    template_name = "audit/detail.html"
    model = AuditEvent
    context_object_name = "event"
    pk_url_kwarg = "id"

    login_url = reverse_lazy("accounts:login")

    def get(self, request, *args, **kwargs):
        if not self.has_permission(request):
            messages.error(request, "No tienes permiso para ver detalles de auditoría.")
            from django.shortcuts import redirect

            return redirect("dashboard")
        return super().get(request, *args, **kwargs)

    def has_permission(self, request):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.user_roles.filter(role__code__in=["R-ADMIN", "R-CONTROL"]).exists()

    def get_object(self):
        event = selectors.get_audit_event_by_id(self.kwargs["id"])
        if event is None:
            from django.http import Http404

            raise Http404("Evento de auditoría no encontrado.")
        return event

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        event = self.object

        # Format changes for display
        changes_display = None
        if event.changes:
            before = event.changes.get("before")
            after = event.changes.get("after")
            if before or after:
                changes_display = {
                    "before": before,
                    "after": after,
                }

        context["changes_display"] = changes_display

        return context


class AuditChainVerifyHtmlView(LoginRequiredMixin, TemplateView):
    """View to verify the audit chain integrity (HTML version)."""

    template_name = "audit/verify.html"

    login_url = reverse_lazy("accounts:login")

    def get(self, request, *args, **kwargs):
        if not self.has_permission(request):
            messages.error(
                request,
                "No tienes permiso para verificar la cadena de auditoría.",
            )
            from django.shortcuts import redirect

            return redirect("dashboard")
        return super().get(request, *args, **kwargs)

    def has_permission(self, request):
        """Only R-ADMIN can verify the chain."""
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.user_roles.filter(role__code="R-ADMIN").exists()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Run verification
        result = selectors.verify_audit_chain()

        context.update(
            {
                "is_valid": result.get("is_valid", False),
                "last_valid_hash": result.get("last_valid_hash", ""),
                "break_point": result.get("break_point"),
                "verification_result": result,
            }
        )

        return context
