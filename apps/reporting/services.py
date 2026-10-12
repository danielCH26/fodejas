"""Reporting service for management reports (CHG-503, CHG-506, CAP-020/027).

All aggregations follow project.md §14.1: internal management reports
for R-COORD / R-JUNTA / R-SECEDU. Responses contain AGGREGATES ONLY —
no PII (AGENTS.md §1, project.md §14).
"""

from decimal import Decimal

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
            Solicitud.objects.values("convocatoria__codigo", "convocatoria__nombre")
            .annotate(total=Count("id"))
            .order_by("convocatoria__codigo")
        )
        por_estado = Solicitud.objects.values("convocatoria__codigo", "estado").annotate(
            total=Count("id")
        )
        estados = {}
        for row in por_estado:
            estados.setdefault(row["convocatoria__codigo"], {})[row["estado"]] = row["total"]
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
            LegalizationProcess.objects.values("convocatoria__codigo", "convocatoria__nombre")
            .annotate(total=Count("id"))
            .order_by("convocatoria__codigo")
        )
        por_estado = LegalizationProcess.objects.values("convocatoria__codigo", "status").annotate(
            total=Count("id")
        )
        estados = {}
        for row in por_estado:
            estados.setdefault(row["convocatoria__codigo"], {})[row["status"]] = row["total"]
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
        por_estado = AcademicRecord.objects.values("status").annotate(total=Count("id"))
        estados = {c["status"]: c["total"] for c in por_estado}
        graduados = estados.get(AcademicRecord.Status.GRADUADO, 0)
        return {
            "total_expedientes": total,
            "por_estado": estados,
            "tasa_graduacion": (round(graduados / total, 4) if total else None),
        }

    @staticmethod
    def _k_suppress(items, count_key):
        """Apply k-anonymity suppression (k=3).

        Groups with < 3 distinct beneficiaries are merged into
        'Otros (suprimido)' to protect PII (project.md §13.2 / Ley 1581/2012).
        Suppressed amounts are summed into Otros (for IES items that have
        total_monto; municipio items omit it).

        Args:
            items: list of dicts with at least {<count_key>: int}.
                IES items also have "total_monto".
            count_key: field name holding the distinct-beneficiary count.
        """
        if not items:
            return items
        protected = [it for it in items if it.get(count_key, 0) >= 3]
        suppressed = [it for it in items if it.get(count_key, 0) < 3]
        otros_count = sum(it.get(count_key, 0) for it in suppressed)
        otros_group = {count_key: otros_count}
        # Add group-by key and total_monto if present in the items
        first_key = list(items[0].keys())[0]
        if first_key == "ies":
            otros_group["ies"] = "Otros (suprimido)"
            otros_monto = sum(Decimal(str(it["total_monto"])) for it in suppressed)
            otros_group["total_monto"] = str(otros_monto)
        elif first_key == "municipio":
            otros_group["municipio"] = "Otros (suprimido)"
        return protected + [otros_group] if suppressed else protected

    @staticmethod
    def estudio_impacto(anio_inicio, anio_fin):
        """Impact study for the CT (project.md §6.1.2, CAP-027).

        Returns aggregate statistics for the period [anio_inicio, anio_fin]
        (inclusive). No PII is included in the response.

        **Cohort year** is the year of ``Solicitud.created_at`` — NOT the
        ``Convocatory.ano`` field (no such field exists; the period of a
        beneficiary's application is the canonical cohort marker).

        **Disbursement join strategy**: ``DisbursementAuthorization`` is joined
        to ``Solicitud`` via
        ``DisbursementAuthorization.legalization_process → (beneficiary,
        convocatoria) → Solicitud`` (unique_together constraint).  A lookup
        dict is built once:
        ``{(convocatoria_id, aspirante_id): solicitud}``
        to avoid N+1 on the disaggregated loops.

        **Monto semantics**: includes ``PAGADO`` and ``ORDENADO`` statuses.
        Consistent with ``ejecucion_presupuestal()`` where ``ordenados``
        excludes ``PAGADO`` (a distinct status representing funds actually
        disbursed), while ``pagados`` is the separate total.  Both
        ``PAGADO`` and ``ORDENADO`` represent authorized/executed amounts
        at different stages of the treasury pipeline; both are relevant
        to impact measurement.

        **K-suppression (k=3)**: applied on ``montos_por_ies`` and
        ``beneficiarios_por_municipio``. Groups with < 3 distinct
        beneficiaries are merged into ``Otros (suprimido)``.
        Amounts from suppressed cells ARE included in Otros.

        **Tasa graduación**: computed over ``AcademicRecord`` instances
        whose ``legalization_process`` belongs to a ``Solicitud`` with
        ``created_at`` year in the cohort range.

        **Tasa retorno**: ``retorno_archipelago=True`` / non-null
        ``retorno_archipelago`` among the same cohort.

        Args:
            anio_inicio: first year of the study period.
            anio_fin: last year of the study period (inclusive).

        Returns:
            dict with keys: beneficiarios_por_cohorte_anio,
            tasa_graduacion, tasa_retorno, montos_por_ies,
            beneficiarios_por_municipio, desglose_por_nivel_formacion,
            desglose_por_convocatoria, periodo.

        Raises:
            ValueError: if the year range is invalid or exceeds 4 years.
        """
        if anio_fin < anio_inicio:
            raise ValueError(
                "Rango de aos invlido: anio_fin debe ser mayor o igual a anio_inicio."
            )
        if anio_fin - anio_inicio > 4:
            raise ValueError(
                "Rango de aos excede el mximo permitido de 4 aos."
            )

        # -----------------------------------------------------------------
        # Build Solicitud lookup: {(convocatoria_id, aspirante_id): solicitud}
        # -----------------------------------------------------------------
        # We only need this for disbursement-to-solicitud lookups.
        # Fetch only the fields we actually use to keep the query light.
        solicitud_lookup = {}
        # Filter solicitudes whose created_at year is in the range
        solicitudes_qs = Solicitud.objects.filter(
            created_at__year__gte=anio_inicio,
            created_at__year__lte=anio_fin,
        ).only(
            "id", "convocatoria_id", "aspirante_id", "ies_nombre",
            "municipio_origen", "datos_academicos"
        )
        for sol in solicitudes_qs:
            key = (sol.convocatoria_id, sol.aspirante_id)
            solicitud_lookup[key] = sol

        # -----------------------------------------------------------------
        # Beneficiarios por cohorte / ao
        # -----------------------------------------------------------------
        beneficiarios_por_cohorte_anio = {}
        for sol in solicitudes_qs:
            year = sol.created_at.year
            beneficiarios_por_cohorte_anio[year] = (
                beneficiarios_por_cohorte_anio.get(year, 0) + 1
            )

        # -----------------------------------------------------------------
        # Desglose por nivel de formacion
        # -----------------------------------------------------------------
        # Parse nivel_formacion from datos_academicos JSON during the pass
        niveles_map = {}
        for sol in solicitudes_qs:
            nivel = sol.datos_academicos.get("nivel_formacion") or ""
            if nivel:
                niveles_map[nivel] = niveles_map.get(nivel, 0) + 1
        desglose_por_nivel_formacion = [
            {"nivel": k, "beneficiarios": v}
            for k, v in sorted(niveles_map.items())
        ]

        # -----------------------------------------------------------------
        # Desglose por convocatoria (from Solicitud pass — beneficiaries)
        # -----------------------------------------------------------------
        conv_beneficiarios = {}  # {convocatoria_id: set(aspirante_ids)}
        conv_montos = {}  # {convocatoria_id: Decimal}
        for sol in solicitudes_qs:
            conv_id = sol.convocatoria_id
            conv_beneficiarios.setdefault(conv_id, set()).add(sol.aspirante_id)

        # -----------------------------------------------------------------
        # Montos por IES + beneficiarios por municipio
        # Build from DisbursementAuthorization → lookup → Solicitud
        # -----------------------------------------------------------------
        # Include PAGADO + ORDENADO (see docstring for rationale)
        disbursements = DisbursementAuthorization.objects.filter(
            status__in=["PAGADO", "ORDENADO"]
        ).select_related(
            "legalization_process__beneficiary",
            "legalization_process__convocatoria",
        )
        ies_beneficiarios = {}  # {ies: set of aspirante_ids}
        ies_montos = {}  # {ies: Decimal}
        municipio_beneficiarios = {}  # {municipio_codigo: set of aspirante_ids}

        for disbursement in disbursements:
            lp = disbursement.legalization_process
            key = (lp.convocatoria_id, lp.beneficiary_id)
            sol = solicitud_lookup.get(key)
            if sol is None:
                continue  # No matching Solicitud in the cohort range

            # Montos por IES — exclude null/empty ies_nombre
            if sol.ies_nombre:
                ies = sol.ies_nombre
                ies_beneficiarios.setdefault(ies, set()).add(sol.aspirante_id)
                ies_montos[ies] = ies_montos.get(ies, Decimal("0")) + disbursement.amount

            # Beneficiarios por municipio
            if sol.municipio_origen_id:
                muncod = sol.municipio_origen.codigo
                municipio_beneficiarios.setdefault(muncod, set()).add(sol.aspirante_id)

            # Montos por convocatoria (desglose_por_convocatoria)
            conv_montos[lp.convocatoria_id] = (
                conv_montos.get(lp.convocatoria_id, Decimal("0"))
                + disbursement.amount
            )

        # Build montos_por_ies with beneficiary counts, then k-suppress
        montos_por_ies_raw = [
            {
                "ies": ies,
                "total_monto": str(monto),
                "beneficiarios": len(ies_beneficiarios[ies]),
            }
            for ies, monto in ies_montos.items()
        ]
        montos_por_ies = ReportingService._k_suppress(
            montos_por_ies_raw, count_key="beneficiarios"
        )

        # Beneficiarios por municipio, then k-suppress
        benef_mun_raw = [
            {
                "municipio": mcod,
                "beneficiarios": len(bens_set),
            }
            for mcod, bens_set in municipio_beneficiarios.items()
        ]
        beneficiarios_por_municipio = ReportingService._k_suppress(
            benef_mun_raw, count_key="beneficiarios"
        )

        # -----------------------------------------------------------------
        # Desglose por convocatoria (finalize)
        # -----------------------------------------------------------------
        desglose_por_convocatoria = []
        for conv_id, beneficiario_set in conv_beneficiarios.items():
            from apps.convocatories.models import Convocatory

            try:
                conv_obj = Convocatory.objects.only("codigo", "nombre").get(id=conv_id)
            except Convocatory.DoesNotExist:
                conv_obj = None
            conv_code = conv_obj.codigo if conv_obj else str(conv_id)
            conv_nombre = conv_obj.nombre if conv_obj else ""
            desglose_por_convocatoria.append({
                "convocatoria": conv_code,
                "nombre": conv_nombre,
                "beneficiarios": len(beneficiario_set),
                "total_monto": str(conv_montos.get(conv_id, Decimal("0"))),
            })

        # -----------------------------------------------------------------
        # Tasa graduacion + tasa retorno
        # AcademicRecord → legalization_process → (beneficiary, convocatoria)
        # must match a Solicitud in the cohort year range.
        # Use Q objects to match EXACT (beneficiary_id, convocatoria_id) pairs
        # from solicitud_lookup (avoids cross-product risk from __in on two
        # separate fields).
        # -----------------------------------------------------------------
        from django.db.models import Q

        cohort_pairs = list(solicitud_lookup.keys())

        # Build Q filter for exact pair matching
        q_pairs = Q()
        for conv_id, asp_id in cohort_pairs:
            q_pairs |= Q(
                legalization_process__beneficiary_id=asp_id,
                legalization_process__convocatoria_id=conv_id,
            )

        cohort_records = AcademicRecord.objects.filter(q_pairs)

        total_expedientes = cohort_records.count()
        graduados_count = cohort_records.filter(
            status=AcademicRecord.Status.GRADUADO
        ).count()
        tasa_graduacion = (
            round(graduados_count / total_expedientes, 4)
            if total_expedientes > 0
            else None
        )

        retorno_total = cohort_records.exclude(
            retorno_archipelago__isnull=True
        ).count()
        retorno_true = cohort_records.filter(
            retorno_archipelago=True
        ).count()
        tasa_retorno = (
            round(retorno_true / retorno_total, 4)
            if retorno_total > 0
            else None
        )

        return {
            "beneficiarios_por_cohorte_anio": {
                str(k): v for k, v in sorted(beneficiarios_por_cohorte_anio.items())
            },
            "tasa_graduacion": tasa_graduacion,
            "tasa_retorno": tasa_retorno,
            "montos_por_ies": montos_por_ies,
            "beneficiarios_por_municipio": beneficiarios_por_municipio,
            "desglose_por_nivel_formacion": desglose_por_nivel_formacion,
            "desglose_por_convocatoria": desglose_por_convocatoria,
            "periodo": {
                "anio_inicio": anio_inicio,
                "anio_fin": anio_fin,
            },
        }

    @staticmethod
    def informe_periodo(anio, trimestre=None):
        """Compose the quarterly or annual management report (§14.1).

        Args:
            anio: report year
            trimestre: 1-4 for a quarterly report, None for annual
        """
        desde = None
        hasta = None
        if trimestre:
            if trimestre not in (1, 2, 3, 4):
                raise ValueError("Trimestre invlido: debe ser 1-4")
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
