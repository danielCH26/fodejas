"""Tests for CHG-502 conflict-of-interest declarations (CAP-018).

Ley 1952/2019 / project.md §6.1.1: the member declares, the simple
majority of the other present voting members approves the impediment,
and the member's vote is not counted for that punto.
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.governance.sessions.models import (
    DeclaracionConflicto,
    MiembroSesion,
    OrdenDelDiaPunto,
    Sesion,
)
from apps.governance.sessions.services import (
    SessionService,
    _add_working_days,
)

User = get_user_model()


def _make_user(n):
    return User.objects.create_user(
        email=f"synthetic-coi-{n}@example.test",
        documento=f"2345678{n:04d}",
        password="test-password-not-real",
        first_name="Miembro",
        last_name="COI",
    )


def _convocar(n=1):
    return SessionService.convocar_sesion(
        organo=Sesion.Organo.JUNTA,
        tipo=Sesion.Tipo.ORDINARIA,
        fecha_hora=_add_working_days(timezone.now(), 10),
        asunto=f"Sesión COI {n}",
        actor=None,
    )


def _setup(n=1):
    """Session with 4 voting members + 1 cargo-exempt, opened, 1 punto."""
    sesion = _convocar(n)
    users = [_make_user(10 * n + i) for i in range(4)]
    exento = _make_user(10 * n + 4)
    SessionService.registrar_asistencia(
        sesion.id,
        [
            {"user_id": u.id, "rol": "Miembro", "asistencia": "PRESENTE"}
            for u in users
        ]
        + [
            {
                "user_id": exento.id,
                "rol": "Secretario",
                "asistencia": "PRESENTE",
                "es_miembro_cargo": True,
            }
        ],
        actor=None,
    )
    punto = SessionService.agregar_punto(
        sesion.id, 1, "Punto con conflicto sintético", actor=None
    )
    SessionService.abrir_sesion(sesion.id, actor=None)
    miembros = [MiembroSesion.objects.get(sesion=sesion, user=u) for u in users]
    miembro_exento = MiembroSesion.objects.get(sesion=sesion, user=exento)
    return sesion, punto, miembros, miembro_exento


@pytest.mark.django_db
class TestDeclararConflicto:
    def test_declaracion_queda_pendiente(self, db):
        sesion, punto, miembros, _ = _setup()
        declaracion = SessionService.declarar_conflicto(
            sesion.id, punto.id, miembros[0].id, "Soy accionista de la IES"
        )
        assert declaracion.estado == DeclaracionConflicto.Estado.PENDIENTE

    def test_voto_bloqueado_con_impedimento_pendiente(self, db):
        sesion, punto, miembros, _ = _setup()
        SessionService.declarar_conflicto(
            sesion.id, punto.id, miembros[0].id, "Declaración sintética"
        )
        with pytest.raises(ValueError, match="impedimento"):
            SessionService.registrar_voto(
                sesion_id=sesion.id,
                punto_id=punto.id,
                miembro_sesion_id=miembros[0].id,
                valor="A_FAVOR",
            )

    def test_requiere_texto(self, db):
        sesion, punto, miembros, _ = _setup()
        with pytest.raises(ValueError, match="texto"):
            SessionService.declarar_conflicto(
                sesion.id, punto.id, miembros[0].id, "  "
            )

    def test_punto_cerrado_no_admite_declaraciones(self, db):
        sesion, punto, miembros, _ = _setup()
        punto.estado = OrdenDelDiaPunto.Estado.APROBADO
        punto.save()
        with pytest.raises(ValueError, match="cerrado"):
            SessionService.declarar_conflicto(
                sesion.id, punto.id, miembros[0].id, "Tarde"
            )


@pytest.mark.django_db
class TestVotarImpedimento:
    def test_declarante_no_vota_su_propio_impedimento(self, db):
        sesion, punto, miembros, _ = _setup()
        declaracion = SessionService.declarar_conflicto(
            sesion.id, punto.id, miembros[0].id, "Declaración sintética"
        )
        with pytest.raises(ValueError, match="propio impedimento"):
            SessionService.votar_impedimento(
                declaracion.id, miembros[0].id, True
            )

    def test_impedimento_aprobado_por_mayoria(self, db):
        """3 habilitados (excl. declarante): mitad+1 = 2 votos a favor."""
        sesion, punto, miembros, _ = _setup()
        declaracion = SessionService.declarar_conflicto(
            sesion.id, punto.id, miembros[0].id, "Declaración sintética"
        )
        SessionService.votar_impedimento(declaracion.id, miembros[1].id, True)
        declaracion.refresh_from_db()
        assert declaracion.estado == DeclaracionConflicto.Estado.PENDIENTE
        SessionService.votar_impedimento(declaracion.id, miembros[2].id, True)
        declaracion.refresh_from_db()
        assert declaracion.estado == DeclaracionConflicto.Estado.APROBADA

    def test_impedimento_rechazado_por_mayoria(self, db):
        sesion, punto, miembros, _ = _setup()
        declaracion = SessionService.declarar_conflicto(
            sesion.id, punto.id, miembros[0].id, "Declaración sintética"
        )
        SessionService.votar_impedimento(declaracion.id, miembros[1].id, False)
        SessionService.votar_impedimento(declaracion.id, miembros[2].id, False)
        declaracion.refresh_from_db()
        assert declaracion.estado == DeclaracionConflicto.Estado.RECHAZADA

    def test_aprobado_excluye_el_voto_del_punto(self, db):
        sesion, punto, miembros, _ = _setup()
        declaracion = SessionService.declarar_conflicto(
            sesion.id, punto.id, miembros[0].id, "Declaración sintética"
        )
        SessionService.votar_impedimento(declaracion.id, miembros[1].id, True)
        SessionService.votar_impedimento(declaracion.id, miembros[2].id, True)
        declaracion.refresh_from_db()
        with pytest.raises(ValueError, match="impedimento"):
            SessionService.registrar_voto(
                sesion_id=sesion.id,
                punto_id=punto.id,
                miembro_sesion_id=miembros[0].id,
                valor="A_FAVOR",
            )

    def test_rechazado_permite_votar(self, db):
        sesion, punto, miembros, _ = _setup()
        declaracion = SessionService.declarar_conflicto(
            sesion.id, punto.id, miembros[0].id, "Declaración sintética"
        )
        SessionService.votar_impedimento(declaracion.id, miembros[1].id, False)
        SessionService.votar_impedimento(declaracion.id, miembros[2].id, False)
        voto = SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembros[0].id,
            valor="A_FAVOR",
        )
        assert voto.valor == "A_FAVOR"

    def test_exento_por_cargo_no_vota_impedimento(self, db):
        sesion, punto, miembros, miembro_exento = _setup()
        declaracion = SessionService.declarar_conflicto(
            sesion.id, punto.id, miembros[0].id, "Declaración sintética"
        )
        with pytest.raises(ValueError, match="cargo"):
            SessionService.votar_impedimento(
                declaracion.id, miembro_exento.id, True
            )

    def test_auditoria_de_impedimento(self, db):
        sesion, punto, miembros, _ = _setup()
        declaracion = SessionService.declarar_conflicto(
            sesion.id, punto.id, miembros[0].id, "Declaración sintética"
        )
        SessionService.votar_impedimento(declaracion.id, miembros[1].id, True)
        SessionService.votar_impedimento(declaracion.id, miembros[2].id, True)
        assert AuditEvent.objects.filter(
            module="governance",
            action="SESSION_IMPEDIMENTO_RESUELTO",
        ).exists()
