"""Tests for impact study (CHG-506, CAP-027).

All fixtures use synthetic data only (AGENTS.md §6.1 — no PII).
Monetary fixtures are hand-computed against known values.
"""

from datetime import UTC
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.models import Role
from apps.accounts.services.assignment import assign_role_to_user
from apps.accounts.services.sync import sync_role_to_group
from apps.applications.models import Solicitud
from apps.convocatories.models import Convocatory
from apps.legalization.models import LegalizationProcess
from apps.reporting.services import ReportingService
from apps.treasury.models import DisbursementAuthorization

User = get_user_model()


def _make_role(code):
    role, _ = Role.objects.get_or_create(
        code=code,
        defaults={"name": code, "type": "interno", "description": code},
    )
    sync_role_to_group(role)
    return role


def _make_user(n, roles=None):
    user = User.objects.create_user(
        email=f"synthetic-imp-{n}@example.test",
        documento=f"9876543{n:04d}",
        password="test-password-not-real",
        first_name="Sintetico",
        last_name="Test",
        is_staff=bool(roles),
        is_superuser=bool(roles),
    )
    for code in roles or []:
        role = _make_role(code)
        assign_role_to_user(user, role)
    return user


def _make_convocatoria(n, estado=Convocatory.Estado.PUBLICADA):
    return Convocatory.objects.create(
        codigo=f"CHG-506-IMP-{n}",
        nombre=f"Convocatoria Impacto {n}",
        estado=estado,
        periodo=f"202{n}-1",
    )


# ---------------------------------------------------------------------------
# Fixtures — internal helpers
# ---------------------------------------------------------------------------


def _make_aware_dt(year, month, day):
    from datetime import datetime
    return datetime(year, month, day, tzinfo=UTC)


def _make_conv_and_solicitudes(n_conv, beneficiary_nums, anio, ies, municipio):
    """Create a Convocatory + Solicitud rows with known cohort year.

    Django auto_now_add=True on Solicitud.created_at auto-sets on INSERT;
    explicit values on save() are ignored.  We use .update() after creation
    to force the cohort year - .update() bypasses pre_save so the value sticks.

    Returns (convocatoria, list_of_solicituds).
    """
    conv = _make_convocatoria(n_conv)
    solicitudes = []
    target_dt = _make_aware_dt(anio, 1, 15)
    for bn in beneficiary_nums:
        asp = _make_user(1000 + bn)
        sol = Solicitud.objects.create(
            convocatoria=conv,
            aspirante=asp,
            estado="radicada",
            ies_nombre=ies,
            datos_academicos={"nivel_formacion": "tecnico"},
            municipio_origen=municipio,
        )
        Solicitud.objects.filter(pk=sol.pk).update(created_at=target_dt)
        sol.refresh_from_db()
        solicitudes.append(sol)
    return conv, solicitudes


def _make_legalization_process(sol):
    """Create LegalizationProcess + force created_at."""
    lp = LegalizationProcess.objects.create(
        beneficiary=sol.aspirante,
        convocatoria=sol.convocatoria,
        status=LegalizationProcess.Status.LEGALIZADO,
    )
    # Match the Solicitud cohort year via created_at
    target_dt = sol.created_at
    LegalizationProcess.objects.filter(pk=lp.pk).update(created_at=target_dt)
    lp.refresh_from_db()
    return lp


def _make_disbursement(lp, amount):
    """Create DisbursementAuthorization with status PAGADO + force created_at."""
    disb = DisbursementAuthorization.objects.create(
        legalization_process=lp,
        amount=Decimal(str(amount)),
        status="PAGADO",
    )
    # Match LP's created_at (which already matches Solicitud's cohort year)
    DisbursementAuthorization.objects.filter(pk=disb.pk).update(created_at=lp.created_at)
    disb.refresh_from_db()
    return disb


# ---------------------------------------------------------------------------
# Service unit tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEstudioImpactoService:
    """RED: test_montos_por_ies_suma_exacta_fixture"""

    def test_montos_por_ies_suma_exacta_fixture(self):
        """Three disbursements of 50/100/150 forUniversidad Test = 300."""
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        # 3 disbursements: 50 + 100 + 150 = 300 for IES "Universidad Test"
        # 3 beneficiaries (k=3 threshold met → not suppressed)
        conv, sols = _make_conv_and_solicitudes(3, [10, 11, 12], 2023, "Universidad Test", san)
        for i, sol in enumerate(sols):
            lp = _make_legalization_process(sol)
            _make_disbursement(lp, [50, 100, 150][i])

        result = ReportingService.estudio_impacto(2023, 2023)
        assert result["beneficiarios_por_cohorte_anio"] == {"2023": 3}
        montos = result["montos_por_ies"]
        ies_entry = next((m for m in montos if m["ies"] == "Universidad Test"), None)
        assert ies_entry is not None, f"Universidad Test not found in {montos}"
        assert Decimal(str(ies_entry["total_monto"])) == Decimal("300")
        assert ies_entry["beneficiarios"] == 3

    def test_montos_ies_ordenado_incluido(self):
        """ORDENADO disbursements count toward montos_por_ies."""
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        # 3 beneficiaries (k=3 threshold met)
        conv, sols = _make_conv_and_solicitudes(4, [11, 12, 13], 2023, "IES Ordenado", san)
        for i, sol in enumerate(sols):
            lp = _make_legalization_process(sol)
            disb = _make_disbursement(lp, 75)
            DisbursementAuthorization.objects.filter(pk=disb.pk).update(status="ORDENADO")

        result = ReportingService.estudio_impacto(2023, 2023)
        ies_entry = next((m for m in result["montos_por_ies"] if m["ies"] == "IES Ordenado"), None)
        assert ies_entry is not None, f"IES Ordenado not found in {result['montos_por_ies']}"
        assert Decimal(str(ies_entry["total_monto"])) == Decimal("225")
        assert ies_entry["beneficiarios"] == 3

    def test_k_suppression_ies_menos_de_3(self):
        """Groups with < 3 beneficiaries are merged into Otros (suprimido)."""
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        # 2 beneficiaries (k=2 < 3 → suppressed)
        conv, sols = _make_conv_and_solicitudes(5, [20, 21], 2023, "IES Pequena", san)
        for i, sol in enumerate(sols):
            lp = _make_legalization_process(sol)
            _make_disbursement(lp, 80)

        result = ReportingService.estudio_impacto(2023, 2023)
        montos = result["montos_por_ies"]
        otros = next((m for m in montos if m["ies"] == "Otros (suprimido)"), None)
        assert otros is not None, f"Otros (suprimido) not found in {montos}"
        assert Decimal(str(otros["total_monto"])) == Decimal("160")
        assert otros["beneficiarios"] == 2
        # The "IES Pequena" entry should be gone
        ies_pequena = next((m for m in montos if m.get("ies") == "IES Pequena"), None)
        assert ies_pequena is None, f"IES Pequena should be suppressed: {montos}"

    def test_k_suppression_ies_3_beneficiarios_no_suprime(self):
        """Exactly 3 beneficiaries meets the k=3 threshold and is NOT suppressed."""
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        # 3 beneficiaries → exactly at threshold, no suppression
        conv, sols = _make_conv_and_solicitudes(6, [30, 31, 32], 2023, "IES Exacta", san)
        for i, sol in enumerate(sols):
            lp = _make_legalization_process(sol)
            _make_disbursement(lp, 100)

        result = ReportingService.estudio_impacto(2023, 2023)
        montos = result["montos_por_ies"]
        otros = next((m for m in montos if m.get("ies") == "Otros (suprimido)"), None)
        assert otros is None, f"No Otros should appear at k=3 threshold: {montos}"
        ies_entry = next((m for m in montos if m["ies"] == "IES Exacta"), None)
        assert ies_entry is not None
        assert Decimal(str(ies_entry["total_monto"])) == Decimal("300")

    def test_k_suppression_municipio_menos_de_3(self):
        """Municipio groups with < 3 beneficiaries are suppressed."""
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        # 2 disbursements from same municipality
        conv, sols = _make_conv_and_solicitudes(7, [40, 41], 2023, "IES Minima", san)
        for i, sol in enumerate(sols):
            lp = _make_legalization_process(sol)
            _make_disbursement(lp, 90)

        result = ReportingService.estudio_impacto(2023, 2023)
        benef_mun = result["beneficiarios_por_municipio"]
        otros = next((m for m in benef_mun if m.get("municipio") == "Otros (suprimido)"), None)
        assert otros is not None, f"Otros (suprimido) not found in {benef_mun}"
        assert otros["beneficiarios"] == 2
        san_entry = next((m for m in benef_mun if m.get("municipio") == "san_andres"), None)
        assert san_entry is None, f"san_andres should be suppressed: {benef_mun}"

    def test_multiple_ies_with_k_suppression(self):
        """Multiple IES groups; only those with < 3 are suppressed into Otros."""
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        # Large IES: 3 beneficiaries (not suppressed)
        conv1, sols1 = _make_conv_and_solicitudes(8, [50, 51, 52], 2023, "IES Grande", san)
        for i, sol in enumerate(sols1):
            lp = _make_legalization_process(sol)
            _make_disbursement(lp, 100)

        # Small IES: 2 beneficiaries (suppressed)
        conv2, sols2 = _make_conv_and_solicitudes(9, [60, 61], 2023, "IES Chica", san)
        for i, sol in enumerate(sols2):
            lp = _make_legalization_process(sol)
            _make_disbursement(lp, 200)

        result = ReportingService.estudio_impacto(2023, 2023)
        montos = result["montos_por_ies"]

        # IES Grande should be present (not suppressed)
        grande = next((m for m in montos if m["ies"] == "IES Grande"), None)
        assert grande is not None
        assert Decimal(str(grande["total_monto"])) == Decimal("300")
        assert grande["beneficiarios"] == 3

        # IES Chica should be absent (suppressed)
        chica = next((m for m in montos if m.get("ies") == "IES Chica"), None)
        assert chica is None, f"IES Chica should be suppressed: {montos}"

        # Otros should absorb IES Chica's 400
        otros = next((m for m in montos if m["ies"] == "Otros (suprimido)"), None)
        assert otros is not None
        assert Decimal(str(otros["total_monto"])) == Decimal("400")
        assert otros["beneficiarios"] == 2

    def test_tasa_graduacion_sin_expedientes(self):
        """Without AcademicRecord entries, tasa_graduacion is None."""
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        # No AcademicRecords for this cohort
        conv, sols = _make_conv_and_solicitudes(10, [70, 71], 2023, "IES Sin Records", san)
        for sol in sols:
            lp = _make_legalization_process(sol)
            _make_disbursement(lp, 50)

        result = ReportingService.estudio_impacto(2023, 2023)
        assert result["tasa_graduacion"] is None
        assert result["tasa_retorno"] is None

    def test_tasa_graduacion_con_expedientes(self):
        """With mixed GRADUADO/ACTIVO records, tasa_graduacion reflects the ratio."""
        from apps.academic_tracking.models import AcademicRecord
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        conv, sols = _make_conv_and_solicitudes(11, [80, 81, 82], 2023, "IES Con Records", san)
        for sol in sols:
            lp = _make_legalization_process(sol)
            _make_disbursement(lp, 60)

        # Create 3 AcademicRecords: 1 GRADUADO, 2 ACTIVO
        status_options = [
            AcademicRecord.Status.GRADUADO,
            AcademicRecord.Status.ACTIVO,
            AcademicRecord.Status.ACTIVO,
        ]
        for i, sol in enumerate(sols):
            lp = LegalizationProcess.objects.get(beneficiary=sol.aspirante, convocatoria=sol.convocatoria)
            AcademicRecord.objects.create(
                legalization_process=lp,
                status=status_options[i],
                semester_count=1,
            )

        result = ReportingService.estudio_impacto(2023, 2023)
        assert float(result["tasa_graduacion"]) == pytest.approx(0.3333, abs=0.0001)

    def test_multiyear_cohort(self):
        """Multi-year query sums beneficiaries across the range."""
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        # 2 beneficiaries in 2022, 3 in 2023 = 5 total
        _make_conv_and_solicitudes(12, [90, 91], 2022, "IES 2022", san)
        _make_conv_and_solicitudes(13, [92, 93, 94], 2023, "IES 2023", san)

        result = ReportingService.estudio_impacto(2022, 2023)
        assert result["beneficiarios_por_cohorte_anio"] == {"2022": 2, "2023": 3}

    def test_year_range_validation(self):
        """Year range exceeding 4 years raises ValueError."""
        with pytest.raises(ValueError, match="excede"):
            ReportingService.estudio_impacto(2020, 2025)

    def test_empty_year_range(self):
        """No solicitudes in range: safe zeros returned."""
        result = ReportingService.estudio_impacto(2000, 2000)
        assert result["beneficiarios_por_cohorte_anio"] == {}
        assert result["montos_por_ies"] == []
        assert result["tasa_graduacion"] is None


def _seed_municipios():
    """Ensure MunicipioIsla seed data exists for tests."""
    from apps.core.models import MunicipioIsla
    if not MunicipioIsla.objects.exists():
        MunicipioIsla.objects.create(codigo="san_andres", nombre="San Andrés")
        MunicipioIsla.objects.create(codigo="providencia", nombre="Providencia")


# ---------------------------------------------------------------------------
# View integration tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEstudioImpactoView:
    """RED: permission + HTTP response + audit trail on anotar_retorno."""

    def test_r_ct_403_no_permiso_escritura(self):
        """R-CT users get 403 on POST/PATCH to anotar_retorno."""
        from apps.academic_tracking.models import AcademicRecord
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        # R-CT user: staff but no academic management role
        rct = User.objects.create_user(
            email="synthetic-imp-rct@example.test",
            documento="98765432000",
            password="test-password-not-real",
            first_name="RCT",
            last_name="User",
            is_staff=False,
            is_superuser=False,
        )
        role_rct = _make_role("R-CT")
        assign_role_to_user(rct, role_rct)
        # Coordinator user
        coord = _make_user(201, roles=["R-COORD"])

        # Setup: Solicitud + LP + AcademicRecord
        conv, sols = _make_conv_and_solicitudes(20, [200], 2023, "IES View Test", san)
        lp = _make_legalization_process(sols[0])
        ar = AcademicRecord.objects.create(
            legalization_process=lp,
            status=AcademicRecord.Status.ACTIVO,
            semester_count=1,
        )

        client = APIClient()
        client.force_authenticate(user=rct)
        resp = client.patch(
            f"/api/academic-tracking/records/{ar.pk}/anotar_retorno/",
            {"retorno_archipelago": True},
            format="json",
        )
        assert resp.status_code == 403

        # R-COORD should be able to PATCH (used by academic_tracking app)
        client.force_authenticate(user=coord)
        resp2 = client.patch(
            f"/api/academic-tracking/records/{ar.pk}/anotar_retorno/",
            {"retorno_archipelago": True},
            format="json",
        )
        assert resp2.status_code == 200

    def test_r_aspirante_403(self):
        """R-ASPIRANTE users cannot access the endpoint at all."""
        from apps.academic_tracking.models import AcademicRecord
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        r_coord = _make_user(210, roles=["R-COORD"])
        r_asp = User.objects.create_user(
            email="synthetic-imp-asp@example.test",
            documento="98765432111",
            password="test-password-not-real",
            first_name="Asp",
            last_name="User",
            is_staff=False,
            is_superuser=False,
        )
        role_asp = _make_role("R-ASPIRANTE")
        assign_role_to_user(r_asp, role_asp)

        conv, sols = _make_conv_and_solicitudes(21, [210], 2023, "IES Aspirante", san)
        lp = _make_legalization_process(sols[0])
        ar = AcademicRecord.objects.create(
            legalization_process=lp,
            status=AcademicRecord.Status.ACTIVO,
            semester_count=1,
        )

        client = APIClient()
        client.force_authenticate(user=r_asp)
        resp = client.patch(
            f"/api/academic-tracking/records/{ar.pk}/anotar_retorno/",
            {"retorno_archipelago": True},
            format="json",
        )
        assert resp.status_code == 403

    def test_audit_fail_rollback(self):
        """When the service raises, the view returns 400 and no audit entry is written."""
        from apps.academic_tracking.models import AcademicRecord
        from apps.audit.models import AuditEvent
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        coord = _make_user(220, roles=["R-COORD"])

        conv, sols = _make_conv_and_solicitudes(22, [220], 2023, "IES Audit", san)
        lp = _make_legalization_process(sols[0])
        ar = AcademicRecord.objects.create(
            legalization_process=lp,
            status=AcademicRecord.Status.ACTIVO,
            semester_count=1,
        )

        initial_count = AuditEvent.objects.count()

        client = APIClient()
        client.force_authenticate(user=coord)
        # Send invalid data (retorno_archipelago must be bool)
        resp = client.patch(
            f"/api/academic-tracking/records/{ar.pk}/anotar_retorno/",
            {"retorno_archipelago": "invalid"},
            format="json",
        )
        assert resp.status_code == 400
        # No audit event was written
        assert AuditEvent.objects.count() == initial_count

    def test_audit_fail_no_partial_update(self):
        """A 400 response leaves the AcademicRecord unchanged."""
        from apps.academic_tracking.models import AcademicRecord
        from apps.core.models import MunicipioIsla

        _seed_municipios()
        san = MunicipioIsla.objects.get(codigo="san_andres")

        coord = _make_user(230, roles=["R-COORD"])

        conv, sols = _make_conv_and_solicitudes(23, [230], 2023, "IES Partial", san)
        lp = _make_legalization_process(sols[0])
        ar = AcademicRecord.objects.create(
            legalization_process=lp,
            status=AcademicRecord.Status.ACTIVO,
            semester_count=1,
            retorno_archipelago=False,
        )

        client = APIClient()
        client.force_authenticate(user=coord)
        resp = client.patch(
            f"/api/academic-tracking/records/{ar.pk}/anotar_retorno/",
            {"retorno_archipelago": "not-a-bool"},
            format="json",
        )
        assert resp.status_code == 400

        # Record unchanged
        ar.refresh_from_db()
        assert ar.retorno_archipelago is False

    def test_estudio_impacto_endpoint_get(self):
        """GET /estudio-impacto/ returns 200 with aggregate data."""
        r_coord = _make_user(240, roles=["R-COORD"])
        client = APIClient()
        client.force_authenticate(user=r_coord)
        resp = client.get("/api/reporting/estudio-impacto/?anio_inicio=2023&anio_fin=2023")
        assert resp.status_code == 200
        data = resp.json()
        assert "beneficiarios_por_cohorte_anio" in data
        assert "tasa_graduacion" in data
        assert "tasa_retorno" in data
        assert "montos_por_ies" in data

    def test_estudio_impacto_unauthenticated_401(self):
        """Unauthenticated GET returns 401."""
        client = APIClient()
        resp = client.get("/api/reporting/estudio-impacto/?anio_inicio=2023&anio_fin=2023")
        assert resp.status_code == 401
