"""API for management reports (CHG-503, CAP-020).

Read-only. Internal roles only (project.md §14.1): R-COORD, R-JUNTA,
R-SECEDU, R-ADMIN. Responses contain aggregates only — no PII.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole
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
