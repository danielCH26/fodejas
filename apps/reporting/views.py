"""API for management reports (CHG-503) and Portal de Transparencia (CHG-504).

Management reports: internal roles only (project.md §14.1): R-COORD,
R-JUNTA, R-SECEDU, R-ADMIN. Responses contain aggregates only — no PII.

Transparencia endpoints: AllowAny, read-only, no PII (project.md §14.2,
AGENTS.md §1, Ley 1581/2012).
"""

from dataclasses import dataclass
from datetime import datetime

from django.views.generic import ListView, TemplateView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole
from apps.reporting.selectors.transparencia import TransparenciaSelectors
from apps.reporting.serializers import (
    TransparenciaActoSerializer,
    TransparenciaConvocatoriaSerializer,
    TransparenciaEstadisticaSerializer,
)
from apps.reporting.services import ReportingService

REPORT_ROLES = ["R-COORD", "R-JUNTA", "R-SECEDU", "R-ADMIN"]
IMPACT_ROLES = REPORT_ROLES + ["R-CT"]


class _ReportingRolePermission(HasAnyRole):
    """HasAnyRole with fixed roles — DRF re-instantiates permission
    classes on every request, so the factory pattern cannot be used in
    a module-level permission_classes list."""

    def __init__(self):
        super().__init__(REPORT_ROLES)


@api_view(["GET"])
@permission_classes([IsAuthenticated, _ReportingRolePermission])
def informe_gestion(request):
    """Management report for a year (and optional quarter)."""
    try:
        anio = int(request.query_params.get("anio", 0))
    except ValueError:
        return Response({"error": "anio debe ser numérico"}, status=400)
    if not anio:
        return Response({"error": "anio es requerido"}, status=400)
    trimestre = request.query_params.get("trimestre")
    if trimestre:
        try:
            trimestre = int(trimestre)
        except ValueError:
            return Response({"error": "trimestre debe ser numérico"}, status=400)
    try:
        informe = ReportingService.informe_periodo(anio, trimestre)
    except ValueError as e:
        return Response({"error": str(e)}, status=400)
    return Response(informe)


# ---------------------------------------------------------------------------
# Portal de Transparencia — public endpoints (CHG-504, CAP-021)
# ---------------------------------------------------------------------------


class _AllowAnyPermission:
    """AllowAny with DRF re-instantiation contract — same pattern as
    _ReportingRolePermission in this module."""

    def __init__(self):
        pass

    def has_permission(self, request, view):
        return True


@api_view(["GET"])
@permission_classes([AllowAny])
def transparencia_actos(request):
    """List published administrative acts (PUBLICADO only).

    GET /api/transparencia/actos/
    """
    datos = TransparenciaSelectors.actos_publicados()
    serializer = TransparenciaActoSerializer(datos, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def transparencia_convocatorias(request):
    """List open and closed convocatorias.

    GET /api/transparencia/convocatorias/
    """
    datos = TransparenciaSelectors.convocatorias_abiertas_cerradas()
    serializer = TransparenciaConvocatoriaSerializer(datos, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([AllowAny])
def transparencia_estadisticas(request):
    """Return aggregate statistics by year and status.

    GET /api/transparencia/estadisticas/
    GET /api/transparencia/estadisticas/?anio=2026

    Returns 400 if anio is not a valid integer.
    """
    anio_raw = request.query_params.get("anio")
    if anio_raw is not None:
        try:
            anio = int(anio_raw)
        except ValueError:
            return Response(
                {"error": "anio debe ser numérico"},
                status=400,
            )
        if not (1000 <= anio <= 9999):
            return Response(
                {"error": "anio debe ser un año de 4 dígitos (1000-9999)"},
                status=400,
            )
    else:
        anio = None

    datos = TransparenciaSelectors.estadisticas_agregadas(anio=anio)
    serializer = TransparenciaEstadisticaSerializer(datos)
    return Response(serializer.data)


# ---------------------------------------------------------------------------
# Portal de Transparencia — public HTML pages (CHG-504, CAP-021)
# ---------------------------------------------------------------------------


@dataclass
class _ActoItem:
    """Plain wrapper so ListView pagination works with dict data."""
    numero: str
    fecha_publicacion: str | None
    pdf_url: str | None
    convocatoria_nombre: str | None


@dataclass
class _ConvocatoriaItem:
    """Plain wrapper so ListView pagination works with dict data."""
    codigo: str
    nombre: str
    estado: str
    fecha_apertura: str | None
    fecha_cierre: str | None


class TransparenciaIndexView(TemplateView):
    """Landing page for the public transparency portal.

    Displays KPI cards from estadisticas_portal() and shortcut cards
    to actos, convocatorias, and estadisticas pages.
    """
    template_name = "transparencia/index.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["kpis"] = TransparenciaSelectors.estadisticas_portal()
        return ctx


class TransparenciaActosView(ListView):
    """Paginated list of published administrative acts (PUBLICADO only).

    Lists numero, fecha_publicacion, convocatoria_nombre, and PDF link.
    """
    template_name = "transparencia/actos.html"
    context_object_name = "actos"
    paginate_by = 10

    def get_queryset(self):
        return [
            _ActoItem(
                numero=d["numero"],
                fecha_publicacion=d["fecha_publicacion"],
                pdf_url=d["pdf_url"],
                convocatoria_nombre=d["convocatoria_nombre"],
            )
            for d in TransparenciaSelectors.actos_publicados()
        ]


class TransparenciaConvocatoriasView(ListView):
    """Paginated list of open and closed convocatorias.

    Lists codigo, nombre, estado badge, and dates.
    """
    template_name = "transparencia/convocatorias.html"
    context_object_name = "convocatorias"
    paginate_by = 10

    def get_queryset(self):
        return [
            _ConvocatoriaItem(
                codigo=d["codigo"],
                nombre=d["nombre"],
                estado=d["estado"],
                fecha_apertura=d["fecha_apertura"],
                fecha_cierre=d["fecha_cierre"],
            )
            for d in TransparenciaSelectors.convocatorias_abiertas_cerradas()
        ]


class TransparenciaEstadisticasView(TemplateView):
    """Aggregate statistics page with optional year filter.

    GET ?anio=YYYY — validated as 4-digit int (1000-9999).
    Invalid anio → graceful fallback to None (no 500).
    """
    template_name = "transparencia/estadisticas.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        # Parse and validate year — graceful fallback to None on bad input
        anio_raw = self.request.GET.get("anio")
        if anio_raw is not None:
            try:
                anio_int = int(anio_raw)
                if 1000 <= anio_int <= 9999:
                    anio = anio_int
                else:
                    anio = None
            except (ValueError, TypeError):
                anio = None
        else:
            anio = None

        ctx["anio"] = anio
        ctx["estadisticas"] = TransparenciaSelectors.estadisticas_agregadas(anio=anio)
        return ctx
class _ImpactStudyPermission(HasAnyRole):
    """HasAnyRole with fixed roles for the impact study endpoint.

    DRF re-instantiates permission classes on every request, so the
    factory pattern cannot be used in a module-level permission_classes
    list.
    """

    def __init__(self):
        super().__init__(IMPACT_ROLES)


@api_view(["GET"])
@permission_classes([IsAuthenticated, _ImpactStudyPermission])
def estudio_impacto_view(request):
    """Impact study for the CT (project.md §6.1.2, CAP-027).

    Returns aggregate statistics for the period [anio_inicio, anio_fin].
    No PII is included in the response.
    """
    # Parse anio_inicio
    raw_inicio = request.query_params.get("anio_inicio")
    if raw_inicio is None:
        return Response({"error": "anio_inicio es requerido"}, status=400)
    try:
        anio_inicio = int(raw_inicio)
    except ValueError:
        return Response({"error": "anio_inicio debe ser numérico"}, status=400)

    # Parse anio_fin
    raw_fin = request.query_params.get("anio_fin")
    if raw_fin is None:
        return Response({"error": "anio_fin es requerido"}, status=400)
    try:
        anio_fin = int(raw_fin)
    except ValueError:
        return Response({"error": "anio_fin debe ser numérico"}, status=400)

    try:
        estudio = ReportingService.estudio_impacto(anio_inicio, anio_fin)
    except ValueError as e:
        return Response({"error": str(e)}, status=400)
    return Response(estudio)
