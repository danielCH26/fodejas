"""API tests for governance sessions (CHG-501, CAP-017)."""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient

from apps.governance.sessions.models import (
    MiembroSesion,
    OrdenDelDiaPunto,
    Sesion,
)
from apps.governance.sessions.services import (
    SessionService,
    _add_working_days,
)

User = get_user_model()


def _make_user(n, staff=False, roles=None):
    user = User.objects.create_user(
        email=f"synthetic-ses-{n}-{n * 11}@example.test",
        documento=f"5678912{n:04d}",
        password="test-password-not-real",
        first_name="Miembro",
        last_name="Sintético",
        is_staff=staff,
        is_superuser=staff,
    )
    for code in roles or []:
        from apps.accounts.models import Role
        from apps.accounts.services.assignment import assign_role_to_user
        from apps.accounts.services.sync import sync_role_to_group

        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={"name": code, "type": "interno", "description": code},
        )
        sync_role_to_group(role)
        assign_role_to_user(user, role)
    return user


def _convocar(n=1, tipo=Sesion.Tipo.ORDINARIA):
    """Convocate a session far enough in the future to pass notice."""
    fecha = _add_working_days(timezone.now(), 10)
    return SessionService.convocar_sesion(
        organo=Sesion.Organo.JUNTA,
        tipo=tipo,
        fecha_hora=fecha,
        asunto=f"Sesión sintética {n}",
        actor=None,
    )


@pytest.fixture
def staff_client(db):
    client = APIClient()
    client.force_authenticate(user=_make_user(1, staff=True, roles=["R-JUNTA", "R-ADMIN"]))
    return client


@pytest.fixture
def plain_client(db):
    client = APIClient()
    client.force_authenticate(user=_make_user(2, staff=False))
    return client


@pytest.fixture
def sesion(db):
    return _convocar()


@pytest.mark.django_db
class TestSesionAPI:
    def test_anonymous_is_unauthorized(self, db):
        assert APIClient().get("/api/sessions/sessions/").status_code == 401

    def test_management_roles_can_list(self, staff_client):
        assert staff_client.get("/api/sessions/sessions/").status_code == 200

    def test_non_management_cannot_list(self, plain_client):
        assert plain_client.get("/api/sessions/sessions/").status_code == 403

    def test_convocar_ordinaria_ok(self, staff_client):
        fecha = _add_working_days(timezone.now(), 10)
        response = staff_client.post(
            "/api/sessions/sessions/",
            {
                "organo": Sesion.Organo.JUNTA,
                "tipo": Sesion.Tipo.ORDINARIA,
                "fecha_hora": fecha.isoformat(),
                "asunto": "Sesión ordinaria sintética",
            },
            format="json",
        )
        assert response.status_code == 201
        assert response.data["estado"] == Sesion.Estado.CONVOCADA

    def test_convocar_anticipo_insuficiente(self, staff_client):
        fecha = _add_working_days(timezone.now(), 3)
        response = staff_client.post(
            "/api/sessions/sessions/",
            {
                "organo": Sesion.Organo.JUNTA,
                "tipo": Sesion.Tipo.ORDINARIA,
                "fecha_hora": fecha.isoformat(),
            },
            format="json",
        )
        assert response.status_code == 400
        assert (
            "working days" in response.data["error"].lower()
            or "días" in response.data["error"].lower()
        )


@pytest.mark.django_db
class TestSesionWorkflowAPI:
    @pytest.fixture
    def sesion_con_miembros(self, db):
        sesion = _convocar(2)
        presidente = _make_user(10, roles=["R-JUNTA"])
        miembro1 = _make_user(11)
        miembro2 = _make_user(12)
        exento = _make_user(13)  # Secretario — attends, never votes
        SessionService.registrar_asistencia(
            sesion.id,
            [
                {"user_id": presidente.id, "rol": "Presidente", "asistencia": "PRESENTE"},
                {"user_id": miembro1.id, "rol": "Miembro", "asistencia": "PRESENTE"},
                {"user_id": miembro2.id, "rol": "Miembro", "asistencia": "VIRTUAL"},
                {
                    "user_id": exento.id,
                    "rol": "Secretario",
                    "asistencia": "PRESENTE",
                    "es_miembro_cargo": True,
                },
            ],
            actor=None,
        )
        punto = SessionService.agregar_punto(
            sesion.id, 1, "Punto sintético del orden del día", actor=None
        )
        return sesion, presidente, miembro1, miembro2, exento, punto

    def test_abrir_requiere_gestion(self, plain_client, sesion_con_miembros):
        sesion, *_ = sesion_con_miembros
        response = plain_client.post(f"/api/sessions/sessions/{sesion.id}/abrir/")
        assert response.status_code == 403

    def test_abrir_con_quorum(self, staff_client, sesion_con_miembros):
        sesion, *_ = sesion_con_miembros
        response = staff_client.post(f"/api/sessions/sessions/{sesion.id}/abrir/")
        assert response.status_code == 200
        assert response.data["status"] == Sesion.Estado.EN_SESION

    def test_voto_solo_miembro_propio(self, staff_client, sesion_con_miembros):
        sesion, presidente, miembro1, miembro2, exento, punto = sesion_con_miembros
        staff_client.post(f"/api/sessions/sessions/{sesion.id}/abrir/")
        otros = _make_user(20)
        otros_client = APIClient()
        otros_client.force_authenticate(user=otros)
        # A non-member cannot vote
        response = otros_client.post(
            f"/api/sessions/sessions/{sesion.id}/votar/",
            {"punto_id": str(punto.id), "valor": "A_FAVOR"},
            format="json",
        )
        assert response.status_code == 403
        # A member votes for themselves
        miembro_client = APIClient()
        miembro_client.force_authenticate(user=miembro1)
        response = miembro_client.post(
            f"/api/sessions/sessions/{sesion.id}/votar/",
            {"punto_id": str(punto.id), "valor": "A_FAVOR"},
            format="json",
        )
        assert response.status_code == 200

    def test_cargo_exempt_cannot_vote(self, sesion_con_miembros):
        sesion, presidente, miembro1, miembro2, exento, punto = sesion_con_miembros
        client = APIClient()
        client.force_authenticate(user=exento)
        SessionService.abrir_sesion(sesion.id)
        response = client.post(
            f"/api/sessions/sessions/{sesion.id}/votar/",
            {"punto_id": str(punto.id), "valor": "A_FAVOR"},
            format="json",
        )
        assert response.status_code == 400

    def test_cerrar_punto_mayoria_simple(self, staff_client, sesion_con_miembros):
        sesion, presidente, miembro1, miembro2, exento, punto = sesion_con_miembros
        SessionService.abrir_sesion(sesion.id)
        m1 = MiembroSesion.objects.get(sesion=sesion, user=miembro1)
        m2 = MiembroSesion.objects.get(sesion=sesion, user=miembro2)
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=m1.id,
            valor="A_FAVOR",
        )
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=m2.id,
            valor="EN_CONTRA",
        )
        # 2 votes emitted: 1 a favor vs 1 en contra → empate = RECHAZADO
        response = staff_client.post(
            f"/api/sessions/sessions/{sesion.id}/cerrar_punto/",
            {"punto_id": str(punto.id)},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["estado"] == OrdenDelDiaPunto.Estado.RECHAZADO
