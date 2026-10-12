"""API for management reports (CHG-503) and Portal de Transparencia (CHG-504).

Management reports: internal roles only (project.md §14.1): R-COORD,
R-JUNTA, R-SECEDU, R-ADMIN. Responses contain aggregates only — no PII.

Transparencia endpoints: AllowAny, read-only, no PII (project.md §14.2,
AGENTS.md §1, Ley 1581/2012).
"""

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
