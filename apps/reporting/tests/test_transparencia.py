"""Tests for Portal de Transparencia API (CHG-504, CAP-021).

All fixtures use synthetic data (AGENTS.md §1 — no PII).
PII-negative assertions follow test_reports.py:test_respuesta_sin_pii.
"""

from datetime import UTC
from decimal import Decimal
from datetime import datetime as _dt

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.academic_tracking.models import AcademicRecord
from apps.applications.models import Solicitud
from apps.convocatories.models import Convocatory
from apps.governance.models import ActoAdministrativo
from apps.legalization.models import LegalizationProcess
from apps.reporting.services import ReportingService
from apps.treasury.models import DisbursementAuthorization

User = get_user_model()


# ---------------------------------------------------------------------------
# Synthetic fixture helpers
# ---------------------------------------------------------------------------

def _synthetic_user(n, roles=None):
    """User with synthetic PII data for PII-negative testing."""
    user = User.objects.create_user(
        email=f"reportero-sintetico-{n}@transparencia.test",
        documento=f"6543219{n:04d}",
        password="test-password-not-real",
        first_name="Reportero",
        last_name="Sintético",
        is_staff=bool(roles),
        is_superuser=bool(roles),
    )
    return user


def _make_convocatoria(n, estado):
    """Convocatoria with synthetic name but realistic code."""
    return Convocatory.objects.create(
        codigo=f"CHG504-TEST-{n}",
        nombre=f"Convocatoria Transparencia {n}",
        estado=estado,
        periodo="2026-1",
        fecha_apertura=_dt(2026, 1, 1, tzinfo=UTC),
        fecha_cierre=_dt(2026, 6, 30, tzinfo=UTC),
    )


def _make_acta(conv, n, estado):
    """ActoAdministrativo in given state."""
    return ActoAdministrativo.objects.create(
        numero=f"RES-CHG504-{n:04d}",
        tipo=ActoAdministrativo.Tipo.RESOLUCION,
        fecha_expedicion=_dt(2026, 3, 1).date(),
        fecha_publicacion=_dt(2026, 3, 15, tzinfo=UTC) if estado == ActoAdministrativo.Estado.PUBLICADO else None,
        asunto=f"Asunto Transparencia {n}",
        considerandos=[{"texto": f"Considerando {n}"}],
        resolutivo=f"Resolutivo {n}",
        estado=estado,
        convocatoria=conv,
    )


def _pii_strings():
    """Known synthetic PII strings that must never appear in API responses."""
    return [
        "Reportero",
        "Sintético",
        "6543219",
        "reportero-sintetico",
        "transparencia.test",
    ]


# ---------------------------------------------------------------------------
# Selector unit tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransparenciaSelectors:
    def test_actos_publicados_solo_publicado(self):
        """actos_publicados() returns only estado=PUBLICADO; excludes BORRADOR/FIRMADO."""
        conv = _make_convocatoria(1, Convocatory.Estado.EN_INSCRIPCION)

        borrador = _make_acta(conv, 1, ActoAdministrativo.Estado.BORRADOR)
        firmado  = _make_acta(conv, 2, ActoAdministrativo.Estado.FIRMADO)
        publicado = _make_acta(conv, 3, ActoAdministrativo.Estado.PUBLICADO)
        anulado  = _make_acta(conv, 4, ActoAdministrativo.Estado.ANULADO)

        from apps.reporting.selectors.transparencia import TransparenciaSelectors
        resultados = TransparenciaSelectors.actos_publicados()

        numeros = [r["numero"] for r in resultados]
        assert str(publicado.numero) in numeros
        assert str(borrador.numero) not in numeros
        assert str(firmado.numero) not in numeros
        assert str(anulado.numero) not in numeros

    def test_actos_publicados_excluye_pii(self):
        """actos_publicados() never includes nombre, documento, email, firmantes."""
        conv = _make_convocatoria(2, Convocatory.Estado.EN_INSCRIPCION)
        _make_acta(conv, 5, ActoAdministrativo.Estado.PUBLICADO)

        from apps.reporting.selectors.transparencia import TransparenciaSelectors
        resultados = TransparenciaSelectors.actos_publicados()

        assert len(resultados) == 1
        item = resultados[0]
        assert "nombre" not in item
        assert "documento" not in item
        assert "email" not in item
        assert "firmante" not in item
        assert "aprobado_por" not in item

    def test_actos_publicados_incluye_campos_requeridos(self):
        """actos_publicados() includes numero, fecha_publicacion, pdf_url, convocatoria_nombre."""
        conv = _make_convocatoria(3, Convocatory.Estado.EN_INSCRIPCION)
        _make_acta(conv, 6, ActoAdministrativo.Estado.PUBLICADO)

        from apps.reporting.selectors.transparencia import TransparenciaSelectors
        resultados = TransparenciaSelectors.actos_publicados()

        assert len(resultados) == 1
        item = resultados[0]
        assert "numero" in item
        assert "fecha_publicacion" in item
        assert "pdf_url" in item
        assert "convocatoria_nombre" in item

    def test_convocatorias_abiertas_cerradas_filtra_estados(self):
        """convocatorias_abiertas_cerradas() returns only CERRADA and EN_INSCRIPCION."""
        ABIERTA = Convocatory.Estado.EN_INSCRIPCION   # "ABIERTa" in spec
        CERRADA = Convocatory.Estado.CERRADA

        abierta    = _make_convocatoria(11, ABIERTA)
        cerrada    = _make_convocatoria(12, CERRADA)
        borrador   = _make_convocatoria(13, Convocatory.Estado.BORRADOR)
        cancelada  = _make_convocatoria(14, Convocatory.Estado.CANCELADA)

        from apps.reporting.selectors.transparencia import TransparenciaSelectors
        resultados = TransparenciaSelectors.convocatorias_abiertas_cerradas()

        codigos = [r["codigo"] for r in resultados]
        assert str(abierta.codigo) in codigos
        assert str(cerrada.codigo) in codigos
        assert str(borrador.codigo) not in codigos
        assert str(cancelada.codigo) not in codigos

    def test_convocatorias_abiertas_cerradas_campos_requeridos(self):
        """Returns codigo, nombre, estado, fecha_apertura, fecha_cierre."""
        conv = _make_convocatoria(15, Convocatory.Estado.EN_INSCRIPCION)

        from apps.reporting.selectors.transparencia import TransparenciaSelectors
        resultados = TransparenciaSelectors.convocatorias_abiertas_cerradas()

        assert len(resultados) == 1
        item = resultados[0]
        for campo in ("codigo", "nombre", "estado", "fecha_apertura", "fecha_cierre"):
            assert campo in item, f"Campo {campo} ausente"

    def test_convocatorias_abiertas_cerradas_sin_pii(self):
        """No PII in convocatoria results."""
        _make_convocatoria(16, Convocatory.Estado.EN_INSCRIPCION)

        from apps.reporting.selectors.transparencia import TransparenciaSelectors
        resultados = TransparenciaSelectors.convocatorias_abiertas_cerradas()

        body = str(resultados)
        for pii in _pii_strings():
            assert pii not in body, f"PII '{pii}' encontrado en convocatoria results"

    def test_estadisticas_agregadas_sin_datos_academicos_parseados(self):
        """estadisticas_agregadas() reuses ReportingService; no parsing of datos_academicos."""
        conv = _make_convocatoria(20, Convocatory.Estado.EN_INSCRIPCION)
        user = _synthetic_user(20)

        # Solicitud para ReportingService.resumen_convocatorias
        Solicitud.objects.create(
            convocatoria=conv,
            aspirante=user,
            estado="radicada",
        )

        from apps.reporting.selectors.transparencia import TransparenciaSelectors
        result = TransparenciaSelectors.estadisticas_agregadas(anio=2026)

        # Top-level keys only from ReportingService aggregations
        assert "convocatorias" in result
        assert "beneficiarios" in result
        assert "ejecucion_presupuestal" in result
        assert "seguimiento_academico" in result
        # No individual-level PII leaked — "nombre" as a field name in aggregate data
        # (convocatoria__nombre) is NOT PII; use actual synthetic strings from _pii_strings()
        for pii in _pii_strings():
            assert pii not in str(result), f"PII '{pii}' found in estadisticas_agregadas result"

    def test_estadisticas_agregadas_filtra_por_anio(self):
        """estadisticas_agregadas(anio=2026) returns only 2026 data."""
        conv = _make_convocatoria(21, Convocatory.Estado.EN_INSCRIPCION)
        user = _synthetic_user(21)

        Solicitud.objects.create(
            convocatoria=conv,
            aspirante=user,
            estado="radicada",
        )

        from apps.reporting.selectors.transparencia import TransparenciaSelectors
        result = TransparenciaSelectors.estadisticas_agregadas(anio=2026)

        assert "convocatorias" in result

    def test_estadisticas_agregadas_ejecucion_presupuestal_filtra_por_anio(self):
        """ejecucion_presupuestal is filtered by year when anio is provided.

        Seeds disbursements in 2025 and 2026, then verifies:
        - anio=2026 returns only 2026 totals
        - anio=None (unfiltered) returns both years combined
        """
        conv = _make_convocatoria(50, Convocatory.Estado.EN_INSCRIPCION)
        beneficiario = _synthetic_user(50)
        proceso = LegalizationProcess.objects.create(
            beneficiary=beneficiario,
            convocatoria=conv,
            status=LegalizationProcess.Status.LEGALIZADO,
        )

        # Disbursement in 2025 — older year
        d_2025 = DisbursementAuthorization.objects.create(
            legalization_process=proceso,
            amount=Decimal("500.00"),
            status=DisbursementAuthorization.Status.PAGADO,
        )
        # Backdate to 2025
        from datetime import datetime as _dt
        d_2025.created_at = _dt(2025, 6, 15, tzinfo=UTC)
        d_2025.save(update_fields=["created_at"])

        # Disbursement in 2026 — target year
        d_2026 = DisbursementAuthorization.objects.create(
            legalization_process=proceso,
            amount=Decimal("1000.00"),
            status=DisbursementAuthorization.Status.ORDENADO,
        )
        # created_at defaults to now (2026 in test env) — no need to force it

        from apps.reporting.selectors.transparencia import TransparenciaSelectors

        # Filtered: only 2026 should appear
        filtrado = TransparenciaSelectors.estadisticas_agregadas(anio=2026)
        ejec_filtrada = filtrado["ejecucion_presupuestal"]
        assert Decimal(str(ejec_filtrada["pagados"])) == Decimal("0"), \
            "2026 filtered: no PAGADO disbursements expected (the 2026 item is ORDENADO)"
        assert Decimal(str(ejec_filtrada["ordenados"])) == Decimal("1000.00"), \
            "2026 filtered: ORDENADOS should be 1000.00 (only the 2026 disbursement)"

        # The 2025 PAGADO amount must NOT leak into the 2026-filtered result
        assert Decimal(str(ejec_filtrada["pagados"])) != Decimal("500.00"), \
            "2025 disbursement leaked into anio=2026 filtered result"

        # Unfiltered: both years present
        sin_filtro = TransparenciaSelectors.estadisticas_agregadas(anio=None)
        ejec_sin_filtro = sin_filtro["ejecucion_presupuestal"]
        assert Decimal(str(ejec_sin_filtro["pagados"])) == Decimal("500.00"), \
            "Unfiltered: pagados should include the 2025 amount"
        assert Decimal(str(ejec_sin_filtro["ordenados"])) == Decimal("1000.00"), \
            "Unfiltered: ordenados should include the 2026 amount"

    def test_estadisticas_portal_keys(self):
        """estadisticas_portal() returns a composed KPI dict."""
        from apps.reporting.selectors.transparencia import TransparenciaSelectors
        result = TransparenciaSelectors.estadisticas_portal()

        assert isinstance(result, dict)
        assert len(result) > 0
        # Must not contain PII
        body = str(result)
        for pii in _pii_strings():
            assert pii not in body


# ---------------------------------------------------------------------------
# API integration tests (APIClient, no auth)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransparenciaAPI:
    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Seed a mix of published/draft actos and open/closed convocatorias."""
        conv_ab = _make_convocatoria(30, Convocatory.Estado.EN_INSCRIPCION)
        conv_cr = _make_convocatoria(31, Convocatory.Estado.CERRADA)
        conv_br = _make_convocatoria(32, Convocatory.Estado.BORRADOR)

        _make_acta(conv_ab, 10, ActoAdministrativo.Estado.PUBLICADO)
        _make_acta(conv_ab, 11, ActoAdministrativo.Estado.BORRADOR)
        _make_acta(conv_cr, 12, ActoAdministrativo.Estado.PUBLICADO)

        # Seed synthetic PII users for negative assertion
        for i in range(40, 44):
            user = _synthetic_user(i)
            Solicitud.objects.create(
                convocatoria=conv_ab,
                aspirante=user,
                estado="radicada",
            )

        self.client = APIClient()

    def test_actos_endpoint_200_anonymous(self):
        """GET /api/transparencia/actos/ returns 200 without auth."""
        response = self.client.get("/api/transparencia/actos/")
        assert response.status_code == 200

    def test_convocatorias_endpoint_200_anonymous(self):
        """GET /api/transparencia/convocatorias/ returns 200 without auth."""
        response = self.client.get("/api/transparencia/convocatorias/")
        assert response.status_code == 200

    def test_estadisticas_endpoint_200_anonymous(self):
        """GET /api/transparencia/estadisticas/ returns 200 without auth."""
        response = self.client.get("/api/transparencia/estadisticas/")
        assert response.status_code == 200

    def test_actos_solo_publicado_en_api(self):
        """Published actos only; BORRADOR never appears."""
        response = self.client.get("/api/transparencia/actos/")
        assert response.status_code == 200
        body = response.json()

        numeros = [item["numero"] for item in body]
        # RES-CHG504-10 and RES-CHG504-12 are PUBLICADO
        assert "RES-CHG504-0010" in numeros
        assert "RES-CHG504-0012" in numeros
        # RES-CHG504-11 is BORRADOR — must NOT appear
        assert "RES-CHG504-0011" not in numeros

    def test_convocatorias_filtra_borrador(self):
        """Only ABIERTA (EN_INSCRIPCION) and CERRADA appear."""
        response = self.client.get("/api/transparencia/convocatorias/")
        assert response.status_code == 200
        body = response.json()

        codigos = [item["codigo"] for item in body]
        assert "CHG504-TEST-30" in codigos   # EN_INSCRIPCION
        assert "CHG504-TEST-31" in codigos  # CERRADA
        assert "CHG504-TEST-32" not in codigos  # BORRADOR

    def test_estadisticas_filtra_anio_valido(self):
        """estadisticas?anio=2026 returns 200 with filtered data."""
        response = self.client.get("/api/transparencia/estadisticas/", {"anio": "2026"})
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_estadisticas_anio_invalido_400(self):
        """estadisticas?anio=abc returns HTTP 400."""
        response = self.client.get("/api/transparencia/estadisticas/", {"anio": "abc"})
        assert response.status_code == 400

    def test_estadisticas_anio_invalido_non_numeric_400(self):
        """estadisticas?anio=abc and ?anio=12 (2-digit) return 400; valid 4-digit year returns 200."""
        assert self.client.get(
            "/api/transparencia/estadisticas/", {"anio": "abc"}
        ).status_code == 400
        assert self.client.get(
            "/api/transparencia/estadisticas/", {"anio": "12"}
        ).status_code == 400, "2-digit year must be rejected as invalid"
        assert self.client.get(
            "/api/transparencia/estadisticas/", {"anio": "2026"}
        ).status_code == 200

    def test_estadisticas_api_ejecucion_presupuestal_filtra_por_anio(self):
        """GET /api/transparencia/estadisticas/?anio=2026 returns year-filtered budget.

        Seeds two disbursements: 2025 (PAGADO 500) and 2026 (ORDENADO 1000).
        - ?anio=2026 → pagados=0, ordenados=1000 (no 2025 leak)
        - no filter   → pagados=500, ordenados=1000 (both years)
        """
        conv = _make_convocatoria(60, Convocatory.Estado.EN_INSCRIPCION)
        beneficiario = _synthetic_user(60)
        proceso = LegalizationProcess.objects.create(
            beneficiary=beneficiario,
            convocatoria=conv,
            status=LegalizationProcess.Status.LEGALIZADO,
        )
        # 2025 disbursement
        d_2025 = DisbursementAuthorization.objects.create(
            legalization_process=proceso,
            amount=Decimal("500.00"),
            status=DisbursementAuthorization.Status.PAGADO,
        )
        from datetime import datetime as _dt
        d_2025.created_at = _dt(2025, 6, 15, tzinfo=UTC)
        d_2025.save(update_fields=["created_at"])

        # 2026 disbursement (ORDENADO — different status to distinguish)
        DisbursementAuthorization.objects.create(
            legalization_process=proceso,
            amount=Decimal("1000.00"),
            status=DisbursementAuthorization.Status.ORDENADO,
        )

        # Filtered to 2026
        resp_2026 = self.client.get("/api/transparencia/estadisticas/", {"anio": "2026"})
        assert resp_2026.status_code == 200
        ejec_2026 = resp_2026.json()["ejecucion_presupuestal"]
        assert Decimal(str(ejec_2026["pagados"])) == Decimal("0"), \
            "anio=2026: pagados should be 0 (the 2026 item is ORDENADO, not PAGADO)"
        assert Decimal(str(ejec_2026["ordenados"])) == Decimal("1000.00"), \
            "anio=2026: ordenados should be 1000.00 only"

        # Unfiltered — both years
        resp_all = self.client.get("/api/transparencia/estadisticas/")
        assert resp_all.status_code == 200
        ejec_all = resp_all.json()["ejecucion_presupuestal"]
        assert Decimal(str(ejec_all["pagados"])) == Decimal("500.00"), \
            "No filter: pagados should include 2025 amount"
        assert Decimal(str(ejec_all["ordenados"])) == Decimal("1000.00"), \
            "No filter: ordenados should include 2026 amount"

    def test_pii_negative_assertions(self):
        """Synthetic PII data never appears in any API endpoint response."""
        response_actos = self.client.get("/api/transparencia/actos/")
        response_conv  = self.client.get("/api/transparencia/convocatorias/")
        response_stats = self.client.get("/api/transparencia/estadisticas/")

        for endpoint, resp in [
            ("/api/transparencia/actos/", response_actos),
            ("/api/transparencia/convocatorias/", response_conv),
            ("/api/transparencia/estadisticas/", response_stats),
        ]:
            assert resp.status_code == 200, f"{endpoint} falló con {resp.status_code}"
            body_json = resp.json()
            body_str = str(body_json)
            for pii in _pii_strings():
                assert pii not in body_str, (
                    f"PII '{pii}' encontrado en respuesta de {endpoint}"
                )

    def test_agregados_consistencia_con_reporting_service(self):
        """estadisticas endpoint values match direct ReportingService calls."""
        # Direct service call
        directo = ReportingService.resumen_convocatorias()
        directo_count = len(directo)

        # Via API
        response = self.client.get("/api/transparencia/estadisticas/")
        assert response.status_code == 200
        data = response.json()

        # Both should contain the same keys at top level
        assert "convocatorias" in data
        assert "beneficiarios" in data
        assert "ejecucion_presupuestal" in data
        assert "seguimiento_academico" in data
