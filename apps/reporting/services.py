"""Reporting service for management reports (CHG-503, CAP-020).

All aggregations follow project.md §14.1: internal management reports
for R-COORD / R-JUNTA / R-SECEDU. Responses contain AGGREGATES ONLY —
no PII (AGENTS.md §1, project.md §14).
"""

from django.db.models import Count, Q, Sum

from apps.academic_tracking.models import AcademicRecord
from apps.applications.models import Solicitud
from apps.legalization.models import LegalizationProcess
from apps.treasury.models import DisbursementAuthorization


class ReportingService:
    """Compose management-report KPIs (project.md §14.1)."""

    @staticmethod
    def resumen_convocatorias():
        """Applications per convocatoria with state breakdown."""
        qs = (
            Solicitud.objects.values(
                "convocatoria__codigo", "convocatoria__nombre"
            )
            .annotate(total=Count("id"))
            .order_by("convocatoria__codigo")
        )
        por_estado = (
            Solicitud.objects.values(
                "convocatoria__codigo", "estado"
            ).annotate(total=Count("id"))
        )
        estados = {}
        for row in por_estado:
            estados.setdefault(row["convocatoria__codigo"], {})[
                row["estado"]
            ] = row["total"]
        return [
            {
                "convocatoria": row["convocatoria__codigo"],
                "nombre": row["convocatoria__nombre"],
                "total": row["total"],
                "por_estado": estados.get(row["convocatoria__codigo"], {}),
            }
            for row in qs
        ]

    @staticmethod
    def beneficiarios_por_convocatoria():
        """Legalization processes per convocatoria with status counts."""
        qs = (
            LegalizationProcess.objects.values(
                "convocatoria__codigo", "convocatoria__nombre"
            )
            .annotate(total=Count("id"))
            .order_by("convocatoria__codigo")
        )
        por_estado = LegalizationProcess.objects.values(
            "convocatoria__codigo", "status"
        ).annotate(total=Count("id"))
        estados = {}
        for row in por_estado:
            estados.setdefault(row["convocatoria__codigo"], {})[
                row["status"]
            ] = row["total"]
        return [
            {
                "convocatoria": row["convocatoria__codigo"],
                "nombre": row["convocatoria__nombre"],
                "beneficiarios": row["total"],
                "por_estado": estados.get(row["convocatoria__codigo"], {}),
            }
            for row in qs
        ]

    @staticmethod
    def ejecucion_presupuestal(desde=None, hasta=None):
        """Disbursement amounts by status within a date range (§14.1)."""
        qs = DisbursementAuthorization.objects.all()
        if desde:
            qs = qs.filter(created_at__date__gte=desde)
        if hasta:
            qs = qs.filter(created_at__date__lte=hasta)
        agregados = qs.aggregate(
            total=Sum("amount"),
            ordenados=Sum("amount", filter=Q(status__in=["ORDENADO", "VENCIDO"])),
            pagados=Sum("amount", filter=Q(status="PAGADO")),
            pendientes=Sum("amount", filter=Q(status="PENDIENTE")),
        )
        conteos = qs.values("status").annotate(total=Count("id"))
        return {
            "total": str(agregados["total"] or 0),
            "ordenados": str(agregados["ordenados"] or 0),
            "pagados": str(agregados["pagados"] or 0),
            "pendientes": str(agregados["pendientes"] or 0),
            "por_estado": {c["status"]: c["total"] for c in conteos},
        }

    @staticmethod
    def seguimiento_academico():
        """Academic tracking states and graduation rate (§14.1)."""
        total = AcademicRecord.objects.count()
        por_estado = AcademicRecord.objects.values("status").annotate(
            total=Count("id")
        )
        estados = {c["status"]: c["total"] for c in por_estado}
        graduados = estados.get(AcademicRecord.Status.GRADUADO, 0)
        return {
            "total_expedientes": total,
            "por_estado": estados,
            "tasa_graduacion": (
                round(graduados / total, 4) if total else None
            ),
        }

    @staticmethod
    def informe_periodo(anio: int, trimestre: int | None = None) -> dict:
        """Compose the quarterly or annual management report (§14.1).

        Args:
            anio: report year
            trimestre: 1-4 for a quarterly report, None for annual
        """
        desde = None
        hasta = None
        if trimestre:
            if trimestre not in (1, 2, 3, 4):
                raise ValueError("Trimestre inválido: debe ser 1-4")
            import calendar

            meses = {1: (1, 3), 2: (4, 6), 3: (7, 9), 4: (10, 12)}
            mes_ini, mes_fin = meses[trimestre]
            desde = f"{anio}-{mes_ini:02d}-01"
            ultimo_dia = calendar.monthrange(anio, mes_fin)[1]
            hasta = f"{anio}-{mes_fin:02d}-{ultimo_dia:02d}"
        return {
            "periodo": {"anio": anio, "trimestre": trimestre},
            "postulaciones": ReportingService.resumen_convocatorias(),
            "beneficiarios": ReportingService.beneficiarios_por_convocatoria(),
            "ejecucion_presupuestal": ReportingService.ejecucion_presupuestal(
                desde=desde, hasta=hasta
            ),
            "seguimiento_academico": ReportingService.seguimiento_academico(),
        }
