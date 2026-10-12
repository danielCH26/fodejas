"""Public selectors for Portal de Transparencia (CHG-504, CAP-021).

All methods expose ONLY aggregate/non-PII data (project.md §14.2,
AGENTS.md §1, Ley 1581/2012). No selector returns nombre, documento,
email, firmantes, datos_academicos, or any individual beneficiary data.

Reuses ReportingService (CHG-503) for aggregation; adds no new DB queries
that expose individual records.
"""

from apps.convocatories.models import Convocatory
from apps.governance.models import ActoAdministrativo
from apps.reporting.services import ReportingService


class TransparenciaSelectors:
    """Public read-only selectors for the transparency portal."""

    @staticmethod
    def actos_publicados():
        """Return list of published actos (PUBLICADO only).

        Each item contains: numero, fecha_publicacion, pdf_url,
        convocatoria_nombre.  Excludes: firmantes, aprobado_por,
        beneficiary data (never queried).

        Returns:
            list[dict]: actos with whitelisted fields only.
        """
        qs = (
            ActoAdministrativo.objects.filter(
                estado=ActoAdministrativo.Estado.PUBLICADO
            )
            .select_related("convocatoria")
            .order_by("-fecha_publicacion", "-created_at")
        )
        return [
            {
                "numero": acto.numero,
                "fecha_publicacion": (
                    acto.fecha_publicacion.isoformat()
                    if acto.fecha_publicacion
                    else None
                ),
                "pdf_url": (
                    acto.pdf.url if acto.pdf else None
                ),
                "convocatoria_nombre": (
                    acto.convocatoria.nombre
                    if acto.convocatoria_id
                    else None
                ),
            }
            for acto in qs
        ]

    @staticmethod
    def convocatorias_abiertas_cerradas():
        """Return open and closed convocatorias.

        Includes: codigo, nombre, estado, fecha_apertura, fecha_cierre.
        Excludes: BORRADOR, CANCELADA, and all draft states.

        Returns:
            list[dict]: convocatorias with whitelisted fields only.
        """
        qs = Convocatory.objects.filter(
            estado__in=[
                # ABIERTA = EN_INSCRIPCION (model uses this value for open-for-apps state)
                Convocatory.Estado.EN_INSCRIPCION,
                Convocatory.Estado.CERRADA,
            ]
        ).order_by("-fecha_apertura")

        return [
            {
                "codigo": conv.codigo,
                "nombre": conv.nombre,
                "estado": conv.estado,
                "fecha_apertura": (
                    conv.fecha_apertura.isoformat()
                    if conv.fecha_apertura
                    else None
                ),
                "fecha_cierre": (
                    conv.fecha_cierre.isoformat()
                    if conv.fecha_cierre
                    else None
                ),
            }
            for conv in qs
        ]

    @staticmethod
    def estadisticas_agregadas(anio=None):
        """Return aggregate statistics by year and status.

        Delegates to ReportingService methods. Year filtering is applied
        only where the underlying service supports it:

        - *ejecucion_presupuestal*: fully filtered by anio via
          ``desde=YYYY-01-01, hasta=YYYY-12-31`` (inclusive date bounds on
          ``created_at__date`` — verified against ``test_reports.py``
          ``test_ejecucion_filtro_por_periodo``).
        - *convocatorias, beneficiarios, seguimiento_academico*:
          no year parameter available in the corresponding ReportingService
          methods; included at full-scope totals with no filtering applied.

        No parsing of datos_academicos, no IES/municipio breakdown
        (deferred to CHG-506).

        Args:
            anio: optional 4-digit year. When provided, the
                  ``ejecucion_presupuestal`` section reflects only
                  disbursements within that calendar year.

        Returns:
            dict: top-level KPI sections from ReportingService.
        """
        desde = f"{anio}-01-01" if anio else None
        hasta = f"{anio}-12-31" if anio else None

        return {
            "convocatorias": ReportingService.resumen_convocatorias(),
            "beneficiarios": ReportingService.beneficiarios_por_convocatoria(),
            "ejecucion_presupuestal": ReportingService.ejecucion_presupuestal(
                desde=desde, hasta=hasta
            ),
            "seguimiento_academico": ReportingService.seguimiento_academico(),
        }

    @staticmethod
    def estadisticas_portal():
        """Return a composed KPI dict for the portal landing page.

        Composes totals from ReportingService into a lightweight public
        dashboard payload. Subset of estadisticas_agregadas() with
        simplified counts (no per-convocatoria breakdown).

        Returns:
            dict: high-level KPIs for the transparency portal landing.
        """
        resumen = ReportingService.resumen_convocatorias()
        beneficiarios = ReportingService.beneficiarios_por_convocatoria()
        presupuesto = ReportingService.ejecucion_presupuestal()
        academico = ReportingService.seguimiento_academico()

        total_postulaciones = sum(r["total"] for r in resumen)
        total_beneficiarios = sum(b["beneficiarios"] for b in beneficiarios)

        return {
            "total_convocatorias": len(resumen),
            "total_postulaciones": total_postulaciones,
            "total_beneficiarios": total_beneficiarios,
            "monto_ordenado": presupuesto.get("ordenados", "0"),
            "monto_pagado": presupuesto.get("pagados", "0"),
            "total_expedientes": academico.get("total_expedientes", 0),
            "tasa_graduacion": academico.get("tasa_graduacion"),
        }
