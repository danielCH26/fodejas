"""Views for audit app."""

import csv
import io
from datetime import datetime
from datetime import timezone as dt_timezone

from django.http import StreamingHttpResponse
from django_filters.rest_framework import DjangoFilterBackend
import rest_framework
from rest_framework import negotiation as drf_negotiation
from rest_framework.utils.mediatypes import _MediaType, media_type_matches, order_by_precedence
from rest_framework import filters, generics, permissions
from rest_framework.response import Response

from apps.accounts.permissions import IsAuditExporter, IsAuditViewer

from .models import AuditEvent
from .selectors import get_audit_events, verify_audit_chain
from .services import verify_chain
from .serializers import AuditChainVerifySerializer, AuditEventSerializer


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


# === CHG-505 / CAP-028 — Audit Export Endpoint ===

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from .export import (
    AUDIT_EXPORT_COLUMNS,
    build_export_row,
    compute_payload_sha256,
    iter_jsonl,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAuditExporter])
def audit_export(request):
    """Export the full audit log as CSV or JSONL (CAP-028).

    NOTE: format_kwarg is set to None on the generated
    WrappedAPIView so DRF's content negotiation does NOT
    interpret ?format= as a renderer suffix (which would raise
    Http404 since we have no CSV/NDJSON renderer).  The view
    handles format validation directly and returns a
    StreamingHttpResponse which bypasses DRF's renderers.

    Query params:
        format  - required: csv or jsonl
        from    - optional ISO datetime (timestamp__gte)
        to      - optional ISO datetime (timestamp__lte)
        entity  - optional, entity name (iexact)
        action  - optional, action type (iexact)

    Returns HTTP 200 with a StreamingHttpResponse and manifest headers:
        X-Audit-Event-Count, X-Audit-Chain-Valid, X-Audit-Chain-Head,
        X-Audit-Chain-Break, X-Audit-Export-SHA256, X-Audit-Generated-At.

    HTTP 400 on invalid format, malformed date, or from > to.
    """
    # --- Validate format ---
    fmt = (request.query_params.get("format") or "").strip().lower()
    if fmt not in ("csv", "jsonl"):
        return Response(
            {"detail": "Parámetro 'format' requerido: 'csv' o 'jsonl'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --- Parse and validate dates ---
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            # Accept ISO 8601 with Z suffix or +00:00
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if dt.tzinfo is None:
            # Normalize naive datetimes to UTC so comparisons never raise
            dt = dt.replace(tzinfo=dt_timezone.utc)
        return dt

    ts_from = _parse_dt(request.query_params.get("from"))
    ts_to = _parse_dt(request.query_params.get("to"))

    if request.query_params.get("from") and ts_from is None:
        return Response(
            {"detail": "Formato de fecha 'from' inválido. Use ISO 8601."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if request.query_params.get("to") and ts_to is None:
        return Response(
            {"detail": "Formato de fecha 'to' inválido. Use ISO 8601."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if ts_from is not None and ts_to is not None and ts_from > ts_to:
        return Response(
            {"detail": "El parámetro 'from' no puede ser posterior a 'to'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    # --- Snapshot seal: clamp the upper bound so both passes see the
    # --- same append-only slice of the ledger.
    # The ledger is append-only (CAP-022), so taking snapshot_at BEFORE
    # the hash pass and clamping timestamp_to to it guarantees the hash
    # pass and the streaming pass observe byte-identical content even if
    # concurrent events are inserted in between.  X-Audit-Generated-At
    # reports exactly this snapshot instant.
    snapshot_at = datetime.now(dt_timezone.utc)
    ts_to_effective = min(ts_to, snapshot_at) if ts_to is not None else snapshot_at

    entity_filter = request.query_params.get("entity")
    action_filter = request.query_params.get("action")

    # One lazy queryset shared by both passes: identical filters, so the
    # append-only invariant makes both evaluations return the same rows.
    queryset = get_audit_events(
        entity=entity_filter,
        action=action_filter,
        timestamp_from=ts_from,
        timestamp_to=ts_to_effective,
    )

    # --- Two-pass SHA-256: hash first, then stream ---
    export_sha256, event_count = compute_payload_sha256(queryset, fmt)

    # --- Chain verification (snapshot at generation time) ---
    chain_result = verify_audit_chain()

    # --- Determine streaming generator ---
    if fmt == "csv":
        # iter_csv yields header first, then rows.  For a clean export
        # file the header is included; compute_payload_sha256 also
        # included it so the hash covers the full file.
        def _gen():
            # Pre-build the header line so we can yield it atomically.
            header_line = (",".join(AUDIT_EXPORT_COLUMNS) + "\n").encode("utf-8")
            yield header_line

            buffer = io.StringIO()
            writer = csv.DictWriter(
                buffer,
                fieldnames=AUDIT_EXPORT_COLUMNS,
                extrasaction="ignore",
                lineterminator="\n",
            )
            for event in queryset.iterator():
                writer.writerow(build_export_row(event))
                yield buffer.getvalue().encode("utf-8")
                buffer.seek(0)
                buffer.truncate(0)

        generator = _gen()
        content_type = "text/csv"
        ext = "csv"
    else:
        generator = iter_jsonl(queryset)
        content_type = "application/x-ndjson"
        ext = "jsonl"

    # --- Build response ---
    generated_at = snapshot_at.isoformat()
    today = snapshot_at.strftime("%Y-%m-%d")
    filename = f"fodejas-audit-{today}.{ext}"

    response = StreamingHttpResponse(generator, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["X-Audit-Event-Count"] = str(event_count)
    response["X-Audit-Chain-Valid"] = "true" if chain_result.get("is_valid") else "false"
    response["X-Audit-Chain-Head"] = chain_result.get("last_valid_hash", "") or ""
    # break_point is UUID or None
    bp = chain_result.get("break_point")
    response["X-Audit-Chain-Break"] = str(bp) if bp else "null"
    response["X-Audit-Export-SHA256"] = export_sha256
    response["X-Audit-Generated-At"] = generated_at

    return response


# Disable DRF format suffix negotiation for the export view.
# DRF interprets ``?format=csv`` as a renderer suffix and raises
# Http404 when no CSV renderer is configured.  Since we return
# StreamingHttpResponse (no DRF rendering), we bypass this entirely.
# Both overrides are needed:
#   format_kwarg=None        - prevents URL suffix (.csv) parsing
#   get_format_suffix=lambda - prevents query-param (?format=csv) parsing
# Both are needed because DRF reads the query param in select_renderer()
# even when format_suffix (from URL suffix) is None.
audit_export.view_class.format_kwarg = None


def _no_format_suffix(cls, **kwargs):
    """Always return None so DRF never reads ?format= from the query string."""
    return None


# Custom content negotiation that NEVER reads ?format= from query params.
# DRF's DefaultContentNegotiation reads the query param even when
# format_suffix (from get_format_suffix / format_kwarg) is None:
#   format = format_suffix or request.query_params.get(format_query_param)
# Since we return StreamingHttpResponse, we have no renderer, and
# filter_renderers raises Http404 for any unknown format.
class _NoQueryFormatNegotiation(rest_framework.negotiation.DefaultContentNegotiation):
    def select_renderer(self, request, renderers, format_suffix=None):
        # Skip query-param-based format override entirely.
        # DRF will use Accept header negotiation instead.
        accepts = self.get_accept_list(request)
        for media_type_set in order_by_precedence(accepts):
            for renderer in renderers:
                for media_type in media_type_set:
                    if media_type_matches(renderer.media_type, media_type):
                        media_type_wrapper = _MediaType(media_type)
                        if (
                            _MediaType(renderer.media_type).precedence >
                            media_type_wrapper.precedence
                        ):
                            full_media_type = ";".join(
                                (renderer.media_type,)
                                + tuple(
                                    "{}={}".format(key, value)
                                    for key, value in media_type_wrapper.params.items()
                                )
                            )
                            return renderer, full_media_type
                        else:
                            return renderer, media_type
        # Fall back to first renderer if no match (prevents 404 in content neg)
        return renderers[0], renderers[0].media_type


audit_export.view_class.get_format_suffix = classmethod(_no_format_suffix)
audit_export.view_class.http_method_names = ["get", "options"]
audit_export.view_class.content_negotiation_class = _NoQueryFormatNegotiation
