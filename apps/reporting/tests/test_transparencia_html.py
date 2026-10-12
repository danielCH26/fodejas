"""HTML portal tests for Portal de Transparencia (CHG-504, CAP-021).

Tests public HTML pages (no auth). These are SEPARATE from the API
tests in test_transparencia.py (Unit A).

All fixtures use synthetic data (AGENTS.md §1 — no PII).
PII-negative assertions follow test_reports.py:test_respuesta_sin_pii.
"""

from datetime import UTC
from datetime import datetime as _dt
from decimal import Decimal

import pytest
from django.test import Client

from apps.convocatories.models import Convocatory
from apps.governance.models import ActoAdministrativo
from apps.governance.models import ListadoDefinitivo
from apps.legalization.models import LegalizationProcess
from apps.reporting.services import ReportingService
from apps.treasury.models import DisbursementAuthorization
from django.contrib.auth import get_user_model

User = get_user_model()


# ---------------------------------------------------------------------------
# Synthetic fixture helpers
# ---------------------------------------------------------------------------

def _synthetic_user(n):
    """User with synthetic PII data for PII-negative testing."""
    return User.objects.create_user(
        email=f"reportero-sintetico-{n}@transparencia.test",
        documento=f"6543219{n:04d}",
        password="test-password-not-real",
        first_name="Reportero",
        last_name="Sintético",
    )


def _pii_strings():
    """Known synthetic PII strings that must never appear in HTML responses."""
    return [
        "Reportero",
        "Sintético",
        "6543219",
        "reportero-sintetico",
        "transparencia.test",
    ]


def _make_convocatoria(n, estado):
    """Convocatoria with synthetic name but realistic code."""
    return Convocatory.objects.create(
        codigo=f"HTML504-{n}",
        nombre=f"Convocatoria Transparencia {n}",
        estado=estado,
        periodo="2026-1",
        fecha_apertura=_dt(2026, 1, 1, tzinfo=UTC),
        fecha_cierre=_dt(2026, 6, 30, tzinfo=UTC),
    )


def _make_acta(conv, n, estado):
    """ActoAdministrativo in given state."""
    return ActoAdministrativo.objects.create(
        numero=f"RES-HTML504-{n:04d}",
        tipo=ActoAdministrativo.Tipo.RESOLUCION,
        fecha_expedicion=_dt(2026, 3, 1).date(),
        fecha_publicacion=_dt(2026, 3, 15, tzinfo=UTC) if estado == ActoAdministrativo.Estado.PUBLICADO else None,
        asunto=f"Asunto Transparencia {n}",
        considerandos=[{"texto": f"Considerando {n}"}],
        resolutivo=f"Resolutivo {n}",
        estado=estado,
        convocatoria=conv,
    )


# ---------------------------------------------------------------------------
# Anonymous HTML page tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransparenciaHTMLPages:
    """All 4 public HTML pages return 200 without authentication."""

    def test_index_returns_200_anonymous(self):
        """GET /transparencia/ returns 200 without auth."""
        client = Client()
        response = client.get("/transparencia/")
        assert response.status_code == 200

    def test_actos_returns_200_anonymous(self):
        """GET /transparencia/actos/ returns 200 without auth."""
        client = Client()
        response = client.get("/transparencia/actos/")
        assert response.status_code == 200

    def test_convocatorias_returns_200_anonymous(self):
        """GET /transparencia/convocatorias/ returns 200 without auth."""
        client = Client()
        response = client.get("/transparencia/convocatorias/")
        assert response.status_code == 200

    def test_estadisticas_returns_200_anonymous(self):
        """GET /transparencia/estadisticas/ returns 200 without auth."""
        client = Client()
        response = client.get("/transparencia/estadisticas/")
        assert response.status_code == 200

    def test_estadisticas_graceful_invalid_year(self):
        """GET /transparencia/estadisticas/?anio=abc returns 200 (no 500)."""
        client = Client()
        response = client.get("/transparencia/estadisticas/", {"anio": "abc"})
        # Spec says: graceful fallback, NOT 500
        assert response.status_code == 200

    def test_estadisticas_valid_year_param(self):
        """GET /transparencia/estadisticas/?anio=2026 returns 200."""
        client = Client()
        response = client.get("/transparencia/estadisticas/", {"anio": "2026"})
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# PII-negative assertions (HTML)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransparenciaHTMLPII:
    """Synthetic PII data never appears in any HTML page."""

    @pytest.fixture(autouse=True)
    def setup_pii_data(self):
        """Seed synthetic users with PII data."""
        conv = _make_convocatoria(90, Convocatory.Estado.EN_INSCRIPCION)
        user = _synthetic_user(90)

        # Create a ListadoDefinitivo so there are beneficiary-like records
        acto = _make_acta(conv, 90, ActoAdministrativo.Estado.PUBLICADO)
        ListadoDefinitivo.objects.create(
            convocatoria=conv,
            ranking=[],  # empty is fine
            acto=acto,
        )

        # Create a legalization + disbursement to populate statistics
        proceso = LegalizationProcess.objects.create(
            beneficiary=user,
            convocatoria=conv,
            status=LegalizationProcess.Status.LEGALIZADO,
        )
        DisbursementAuthorization.objects.create(
            legalization_process=proceso,
            amount=Decimal("500.00"),
            status=DisbursementAuthorization.Status.PAGADO,
        )

    def test_index_no_pii(self):
        """Landing page contains no synthetic PII."""
        client = Client()
        response = client.get("/transparencia/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        for pii in _pii_strings():
            assert pii not in html, f"PII '{pii}' found in /transparencia/ HTML"

    def test_actos_no_pii(self):
        """Actos page contains no synthetic PII."""
        client = Client()
        response = client.get("/transparencia/actos/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        for pii in _pii_strings():
            assert pii not in html, f"PII '{pii}' found in /transparencia/actos/ HTML"

    def test_convocatorias_no_pii(self):
        """Convocatorias page contains no synthetic PII."""
        client = Client()
        response = client.get("/transparencia/convocatorias/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        for pii in _pii_strings():
            assert pii not in html, f"PII '{pii}' found in /transparencia/convocatorias/ HTML"

    def test_estadisticas_no_pii(self):
        """Estadisticas page contains no synthetic PII."""
        client = Client()
        response = client.get("/transparencia/estadisticas/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        for pii in _pii_strings():
            assert pii not in html, f"PII '{pii}' found in /transparencia/estadisticas/ HTML"


# ---------------------------------------------------------------------------
# Actos filtering (PUBLICADO only)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransparenciaHTMLActos:
    """Only actos with estado=PUBLICADO appear in the actos HTML page."""

    def test_borrador_acto_absent_from_actos_page(self):
        """Acto with BORRADOR does NOT appear in /transparencia/actos/."""
        conv = _make_convocatoria(70, Convocatory.Estado.EN_INSCRIPCION)
        _make_acta(conv, 70, ActoAdministrativo.Estado.BORRADOR)

        client = Client()
        response = client.get("/transparencia/actos/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "RES-HTML504-0070" not in html, "BORRADOR acto should not appear"

    def test_publicado_acto_present_in_actos_page(self):
        """Acto with PUBLICADO appears in /transparencia/actos/."""
        conv = _make_convocatoria(71, Convocatory.Estado.EN_INSCRIPCION)
        _make_acta(conv, 71, ActoAdministrativo.Estado.PUBLICADO)

        client = Client()
        response = client.get("/transparencia/actos/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "RES-HTML504-0071" in html, "PUBLICADO acto should appear"


# ---------------------------------------------------------------------------
# Convocatorias filtering (EN_INSCRIPCION and CERRADA only)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransparenciaHTMLConvocatorias:
    """Only EN_INSCRIPCION and CERRADA convocatorias appear."""

    def test_borrador_convocatoria_absent(self):
        """BORRADOR convocatoria does NOT appear in /transparencia/convocatorias/."""
        _make_convocatoria(80, Convocatory.Estado.BORRADOR)

        client = Client()
        response = client.get("/transparencia/convocatorias/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "HTML504-80" not in html

    def test_cancelada_convocatoria_absent(self):
        """CANCELADA convocatoria does NOT appear in /transparencia/convocatorias/."""
        _make_convocatoria(81, Convocatory.Estado.CANCELADA)

        client = Client()
        response = client.get("/transparencia/convocatorias/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "HTML504-81" not in html

    def test_en_inscripcion_convocatoria_present(self):
        """EN_INSCRIPCION convocatoria appears in /transparencia/convocatorias/."""
        _make_convocatoria(82, Convocatory.Estado.EN_INSCRIPCION)

        client = Client()
        response = client.get("/transparencia/convocatorias/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "HTML504-82" in html

    def test_cerrada_convocatoria_present(self):
        """CERRADA convocatoria appears in /transparencia/convocatorias/."""
        _make_convocatoria(83, Convocatory.Estado.CERRADA)

        client = Client()
        response = client.get("/transparencia/convocatorias/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        assert "HTML504-83" in html


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransparenciaHTMLPagination:
    """Actos page is paginated (10 per page)."""

    def test_actos_page_1_has_10(self):
        """Page 1 of actos contains exactly 10 items."""
        conv = _make_convocatoria(60, Convocatory.Estado.EN_INSCRIPCION)
        # Create 11 published actos
        for i in range(60, 71):
            _make_acta(conv, i, ActoAdministrativo.Estado.PUBLICADO)

        client = Client()
        response = client.get("/transparencia/actos/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # Page 1 should have 10 items (check for exactly 10 table rows in tbody)
        import re
        tbody_rows = re.findall(r'<tr>.*?</tr>', html, re.DOTALL)
        # Filter to rows that contain RES-HTML504-00XX (actual actos, not headers)
        acto_rows = [r for r in tbody_rows if 'RES-HTML504-00' in r]
        assert len(acto_rows) == 10, f"Expected 10 actos on page 1, got {len(acto_rows)}"
        # All actos on page 1 should be from the seeded range 60-70
        for row in acto_rows:
            # Extract the acto number
            match = re.search(r'RES-HTML504-(\d+)', row)
            assert match, f"Could not find acto number in row: {row[:100]}"
            num = int(match.group(1))
            assert 60 <= num <= 70, f"Acto {num} not in seeded range [60-70]"

    def test_actos_page_2_has_remaining(self):
        """Page 2 of actos contains exactly 1 item (the 11th acto)."""
        conv = _make_convocatoria(61, Convocatory.Estado.EN_INSCRIPCION)
        # Create 11 published actos
        for i in range(61, 72):
            _make_acta(conv, i, ActoAdministrativo.Estado.PUBLICADO)

        client = Client()
        response = client.get("/transparencia/actos/", {"page": "2"})
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # Page 2 should have 1 item
        import re
        tbody_rows = re.findall(r'<tr>.*?</tr>', html, re.DOTALL)
        acto_rows = [r for r in tbody_rows if 'RES-HTML504-00' in r]
        assert len(acto_rows) == 1, f"Expected 1 acto on page 2, got {len(acto_rows)}"
        # The item on page 2 should be from the seeded range 61-71
        match = re.search(r'RES-HTML504-(\d+)', acto_rows[0])
        assert match
        num = int(match.group(1))
        assert 61 <= num <= 71, f"Acto {num} not in seeded range [61-71]"


# ---------------------------------------------------------------------------
# Nav link in base template
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestTransparenciaNavLink:
    """The base template includes a 'Transparencia' nav link."""

    def test_nav_link_in_index_response(self):
        """Landing page HTML contains a link referencing the transparencia index."""
        client = Client()
        response = client.get("/transparencia/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # The link href should contain 'transparencia'
        assert "transparencia" in html.lower()
        # Specifically, it should link to the index page or actos/convocatorias/estadisticas
        assert "/transparencia/" in html or "transparencia:index" in html

    def test_nav_link_in_base_html(self):
        """The nav link to transparencia is present on the base template."""
        client = Client()
        # Use a page that definitely renders the base template
        # Login page renders base.html
        response = client.get("/transparencia/")
        assert response.status_code == 200
        html = response.content.decode("utf-8")
        # Look for the nav link text
        assert "Transparencia" in html
        # Verify it links to the transparencia portal
        assert "/transparencia/" in html
