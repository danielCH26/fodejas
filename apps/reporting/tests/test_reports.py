"""Tests for management reports (CHG-503, CAP-020).

All fixtures use synthetic data (AGENTS.md §6.1 — no PII). KPI values
are verified against hand-computed aggregates from the seeded data.
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


def _make_user(n, roles=None):
    user = User.objects.create_user(
        email=f"synthetic-rep-{n}-{n * 13}@example.test",
        documento=f"6543219{n:04d}",
        password="test-password-not-real",
        first_name="Reportero",
        last_name="Sintético",
        is_staff=bool(roles),
        is_superuser=bool(roles),
    )
    for code in roles or []:
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={"name": code, "type": "interno", "description": code},
        )
        sync_role_to_group(role)
        assign_role_to_user(user, role)
    return user


def _make_convocatoria(n):
    return Convocatory.objects.create(
        codigo=f"CHG-503-REP-{n}",
        nombre=f"Convocatoria Reportes {n}",
        estado=Convocatory.Estado.EN_INSCRIPCION,
    )


def _make_solicitud(conv, n, estado="radicada"):
    aspirante = _make_user(900 + n)
    return Solicitud.objects.create(
        convocatoria=conv,
        aspirante=aspirante,
        estado=estado,
    )


def _make_legalized(conv, n):
    beneficiario = _make_user(800 + n)
    return LegalizationProcess.objects.create(
        beneficiary=beneficiario,
        convocatoria=conv,
        status=LegalizationProcess.Status.LEGALIZADO,
    )


@pytest.mark.django_db
class TestKpis:
    def test_resumen_convocatorias_agrega_por_estado(self, db):
        conv = _make_convocatoria(1)
        _make_solicitud(conv, 1, "radicada")
        _make_solicitud(conv, 2, "radicada")
        _make_solicitud(conv, 3, "verificada")
        resumen = ReportingService.resumen_convocatorias()
        entry = next(r for r in resumen if r["convocatoria"] == conv.codigo)
        assert entry["total"] == 3
        assert entry["por_estado"]["radicada"] == 2
        assert entry["por_estado"]["verificada"] == 1

    def test_beneficiarios_por_convocatoria(self, db):
        conv = _make_convocatoria(2)
        _make_legalized(conv, 1)
        _make_legalized(conv, 2)
        beneficiarios = ReportingService.beneficiarios_por_convocatoria()
        entry = next(b for b in beneficiarios if b["convocatoria"] == conv.codigo)
        assert entry["beneficiarios"] == 2

    def test_ejecucion_presupuestal_suma_por_estado(self, db):
        conv = _make_convocatoria(3)
        proceso = _make_legalized(conv, 3)
        DisbursementAuthorization.objects.create(
            legalization_process=proceso,
            amount=Decimal("1000.00"),
            status=DisbursementAuthorization.Status.PAGADO,
        )
        DisbursementAuthorization.objects.create(
            legalization_process=proceso,
            amount=Decimal("500.00"),
            status=DisbursementAuthorization.Status.ORDENADO,
        )
        DisbursementAuthorization.objects.create(
            legalization_process=proceso,
            amount=Decimal("250.00"),
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        ejecucion = ReportingService.ejecucion_presupuestal()
        assert Decimal(str(ejecucion["pagados"])) == Decimal("1000.00")
        assert Decimal(str(ejecucion["ordenados"])) == Decimal("500.00")
        assert Decimal(str(ejecucion["pendientes"])) == Decimal("250.00")

    def test_ejecucion_filtro_por_periodo(self, db):
        conv = _make_convocatoria(4)
        proceso = _make_legalized(conv, 4)
        viejo = DisbursementAuthorization.objects.create(
            legalization_process=proceso,
            amount=Decimal("999.00"),
            status=DisbursementAuthorization.Status.PAGADO,
        )
        # Force the old disbursement into a previous year.
        from datetime import datetime as _dt

        viejo.created_at = _dt(2020, 1, 1, tzinfo=UTC)
        viejo.save()
        DisbursementAuthorization.objects.create(
            legalization_process=proceso,
            amount=Decimal("100.00"),
            status=DisbursementAuthorization.Status.PAGADO,
        )
        ejecucion = ReportingService.ejecucion_presupuestal(desde="2026-01-01", hasta="2026-12-31")
        assert Decimal(str(ejecucion["pagados"])) == Decimal("100.00")

    def test_informe_periodo_trimestral(self, db):
        conv = _make_convocatoria(5)
        _make_solicitud(conv, 5)
        informe = ReportingService.informe_periodo(2026, 3)
        assert informe["periodo"] == {"anio": 2026, "trimestre": 3}
        assert "postulaciones" in informe
        assert "ejecucion_presupuestal" in informe
        assert "seguimiento_academico" in informe

    def test_informe_periodo_invalido(self, db):
        with pytest.raises(ValueError, match="Trimestre"):
            ReportingService.informe_periodo(2026, 9)


@pytest.mark.django_db
class TestReportingAPI:
    def test_acceso_requiere_rol(self, db):
        reporter = _make_user(60, roles=["R-COORD"])
        client = APIClient()
        client.force_authenticate(user=reporter)
        response = client.get("/api/reporting/gestion/", {"anio": 2026})
        assert response.status_code == 200

    def test_rol_ajeno_403(self, db):
        ajeno = _make_user(61, roles=["R-ASPIRANTE"])
        client = APIClient()
        client.force_authenticate(user=ajeno)
        response = client.get("/api/reporting/gestion/", {"anio": 2026})
        assert response.status_code == 403

    def test_anonimo_401(self, db):
        assert APIClient().get("/api/reporting/gestion/", {"anio": 2026}).status_code == 401

    def test_anio_requerido(self, db):
        reporter = _make_user(62, roles=["R-JUNTA"])
        client = APIClient()
        client.force_authenticate(user=reporter)
        response = client.get("/api/reporting/gestion/")
        assert response.status_code == 400

    def test_respuesta_sin_pii(self, db):
        conv = _make_convocatoria(6)
        _make_solicitud(conv, 6)
        reporter = _make_user(63, roles=["R-COORD"])
        client = APIClient()
        client.force_authenticate(user=reporter)
        response = client.get("/api/reporting/gestion/", {"anio": 2026})
        body = str(response.content)
        # Synthetic emails/names/documents must never leak.
        assert "synthetic-rep" not in body
        assert "Reportero" not in body
        assert "6543219" not in body
