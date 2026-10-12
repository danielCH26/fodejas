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
            return Response(
                {"error": "trimestre debe ser numérico"}, status=400
            )
    try:
        informe = ReportingService.informe_periodo(anio, trimestre)
    except ValueError as e:
        return Response({"error": str(e)}, status=400)
    return Response(informe)
