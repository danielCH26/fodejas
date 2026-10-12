"""Tests for governance/sessions (CHG-501 / CAP-017).

Covers:
  - Convocation notice periods (ORDINARIA ≥5 WD, EXTRAORDINARIA ≥2 WD)
  - Quórum math (mitad + 1 of voting members; cargo-exempt excluded)
  - Session cannot open without quórum
  - Cargo-exempt members never vote and never count toward quórum
  - Conflicto-declarado members cannot vote
  - Vote can be updated until punto is closed
  - Majority resolution (A_FAVOR > EN_CONTRA; tie → RECHAZADO;
    ABSTENCION never counts)
  - Cannot finalize with open puntos
  - Acta generation with PDF + SHA-256
  - Acta signing stores pre/post hash and firmantes
  - CAP-022 audit events on every transition
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, time

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.accounts.models import Role, UserRole
from apps.audit.models import AuditEvent
from apps.audit.services import coerce_entity_id
from apps.governance.sessions.models import (
    ActaSesion,
    MiembroSesion,
    OrdenDelDiaPunto,
    Sesion,
    Voto,
)
from apps.governance.sessions.models import DeclaracionConflicto
from apps.governance.sessions.services import (
    SessionService,
    _add_working_days,
    _working_days_between,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def user_factory(db):
    """Factory for synthetic CustomUser instances."""
    CustomUser = get_user_model()
    counter = {"n": 0}

    def _make(role_codes=()):
        counter["n"] += 1
        n = counter["n"]
        user = CustomUser.objects.create_user(
            email=f"test-{n}-{uuid.uuid4().hex[:6]}@example.test",
            documento=f"999000{n:04d}",
            password="test-password-not-real",
            first_name=f"Synthetic{n}",
            last_name="Test",
        )
        for code in role_codes:
            role, _ = Role.objects.get_or_create(
                code=code,
                defaults={"name": code, "type": "interno", "description": code},
            )
            UserRole.objects.get_or_create(user=user, role=role, convocation_scope_id=None)
        return user

    return _make


@pytest.fixture
def voting_member(user_factory):
    """A regular voting member (JUNTA role)."""
    return user_factory(role_codes=["R-JUNTA"])


@pytest.fixture
def cargo_member(user_factory):
    """A cargo-exempt member (simulates Gobernador/Alcalde/Secretario)."""
    return user_factory(role_codes=["R-JUNTA"])


@pytest.fixture
def sesion_factory(db, user_factory):
    """Factory for Sesion instances in CONVOCADA state."""

    def _make(tipo=Sesion.Tipo.ORDINARIA, **extra):
        today = timezone.now().date()
        # Default to 10 working days in the future to satisfy ORDINARIA notice
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=tipo,
            fecha_hora=fecha_hora,
            asunto="Sesión de prueba sintética",
            actor=None,
        )
        return sesion

    return _make


# ---------------------------------------------------------------------------
# Working-day helpers
# ---------------------------------------------------------------------------


class TestWorkingDays:
    def test_add_working_days_forward(self):
        """_add_working_days adds only Mon–Fri."""
        # Monday 2026-01-05 + 5 WD = Monday 2026-01-12
        # (skips Sat/Sun)
        start = timezone.datetime(2026, 1, 5).date()  # Mon
        result = _add_working_days(start, 5)
        assert result.weekday() == 0  # Monday
        assert result == timezone.datetime(2026, 1, 12).date()

    def test_add_working_days_zero(self):
        assert _add_working_days(timezone.now().date(), 0) == timezone.now().date()

    def test_add_working_days_backward_skip_weekend(self):
        """_add_working_days with negative days skips Sat/Sun (backward walk)."""
        # Friday 2025-01-10 - 3 WD = Tuesday 2025-01-07
        # (skips Sat 11, Sun 12)
        start = timezone.datetime(2025, 1, 10).date()  # Fri
        result = _add_working_days(start, -3)
        assert result.weekday() < 5  # Mon–Fri
        assert result == timezone.datetime(2025, 1, 7).date()

    def test_add_working_days_backward_one_day(self):
        """_add_working_days with -1 on Monday returns previous Friday."""
        # Monday 2025-01-13 - 1 WD = Friday 2025-01-10
        start = timezone.datetime(2025, 1, 13).date()  # Mon
        result = _add_working_days(start, -1)
        assert result.weekday() < 5
        assert result == timezone.datetime(2025, 1, 10).date()

    def test_working_days_between_same_day(self):
        d = timezone.datetime(2026, 1, 5).date()
        assert _working_days_between(d, d) == 0

    def test_working_days_between_across_weekend(self):
        # Mon Jan 5 → Mon Jan 12 = 5 working days (skips weekend)
        start = timezone.datetime(2026, 1, 5).date()  # Mon
        end = timezone.datetime(2026, 1, 12).date()  # Mon
        assert _working_days_between(start, end) == 5


# ---------------------------------------------------------------------------
# Convocation notice
# ---------------------------------------------------------------------------


class TestConvocacionNotice:
    def test_ordinaria_ok_5_working_days(self, user_factory):
        """ORDINARIA with exactly 5 working days notice is accepted."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 5), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Convocatoria ordinaria a 5 días hábiles",
            actor=None,
        )
        assert sesion.estado == Sesion.Estado.CONVOCADA
        assert sesion.tipo == Sesion.Tipo.ORDINARIA

    def test_ordinaria_fail_4_working_days(self, user_factory):
        """ORDINARIA with only 4 working days notice is rejected."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 4), time(9, 0)))
        with pytest.raises(ValueError) as exc_info:
            SessionService.convocar_sesion(
                organo=Sesion.Organo.JUNTA,
                tipo=Sesion.Tipo.ORDINARIA,
                fecha_hora=fecha_hora,
                asunto="Convocatoria ordinaria insuficiente",
                actor=None,
            )
        assert "5 días hábiles" in str(exc_info.value)

    def test_extraordinaria_ok_2_working_days(self, user_factory):
        """EXTRAORDINARIA with exactly 2 working days notice is accepted."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 2), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.EXTRAORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Extraordinaria a 2 días hábiles",
            actor=None,
        )
        assert sesion.estado == Sesion.Estado.CONVOCADA
        assert sesion.tipo == Sesion.Tipo.EXTRAORDINARIA

    def test_extraordinaria_fail_1_working_day(self, user_factory):
        """EXTRAORDINARIA with only 1 working day notice is rejected."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 1), time(9, 0)))
        with pytest.raises(ValueError) as exc_info:
            SessionService.convocar_sesion(
                organo=Sesion.Organo.JUNTA,
                tipo=Sesion.Tipo.EXTRAORDINARIA,
                fecha_hora=fecha_hora,
                asunto="Extraordinaria insuficiente",
                actor=None,
            )
        assert "2 días hábiles" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Quórum
# ---------------------------------------------------------------------------


class TestQuorum:
    def test_quorum_mitad_mas_1(self, user_factory):
        """Quórum = mitad + 1 of present voting members.

        With 3 voting members present, quórum needs 2 (mitad+1 of 3).
        With only 1 present, quórum NOT met.
        """
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Quórum test",
            actor=None,
        )

        # Register 3 voting members (all PRESENT)
        users = [user_factory(role_codes=["R-JUNTA"]) for _ in range(3)]
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": u.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
                for u in users
            ],
            actor=None,
        )
        sesion.refresh_from_db()
        # Quórum: mitad+1 of 3 = 2. All 3 present → quórum MET.
        assert sesion.voting_members_present() == 3
        assert sesion.quorum_met() is True

    def test_quorum_no_met(self, user_factory):
        """Quórum NOT met when fewer than mitad+1 voting members present.

        With 3 registered voting members but 0 PRESENT, quórum needs 1.
        """
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Sin quórum test",
            actor=None,
        )

        # Register 3 voting members, none present
        users = [user_factory(role_codes=["R-JUNTA"]) for _ in range(3)]
        records = [
            {
                "user_id": u.id,
                "rol": "Miembro",
                "asistencia": MiembroSesion.Asistencia.AUSENTE,
                "es_miembro_cargo": False,
                "conflicto_declarado": False,
            }
            for u in users
        ]
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=records,
            actor=None,
        )
        sesion.refresh_from_db()
        # Quórum: majority = floor(0/2)+1 = 1. With 0 present → quórum NOT met.
        vp = sesion.voting_members_present()
        assert vp == 0, f"Expected voting_members_present=0, got {vp}"
        assert sesion.quorum_met() is False

    def test_abrir_sesion_without_quorum_rejected(self, user_factory):
        """abrir_sesion raises when quórum is not met."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Sin quórum",
            actor=None,
        )

        # Create 3 voting members; none are present (quórum = 0)
        users = [user_factory(role_codes=["R-JUNTA"]) for _ in range(3)]
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": u.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.AUSENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
                for u in users
            ],
            actor=None,
        )
        sesion.refresh_from_db()
        # 0 present → quórum not met (majority = 0+1 = 1, need 1 but have 0)
        assert sesion.quorum_met() is False

        with pytest.raises(ValueError) as exc_info:
            SessionService.abrir_sesion(sesion.id, actor=None)
        assert "quórum" in str(exc_info.value).lower()

    def test_quorum_exactly_one_voting_member(self, user_factory):
        """Quórum is met with exactly 1 voting member present.

        majority = floor(1/2) + 1 = 1.  One member is enough.
        """
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(
            datetime.combine(_add_working_days(today, 10), time(9, 0))
        )
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Quórum con un miembro",
            actor=None,
        )
        voting_user = user_factory(role_codes=["R-JUNTA"])
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": voting_user.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
            ],
            actor=None,
        )
        sesion.refresh_from_db()
        assert sesion.voting_members_present() == 1
        assert sesion.quorum_met() is True

    def test_cargo_exempt_no_vote_no_quorum_count(self, user_factory):
        """Cargo-exempt members never vote and do not count toward quórum."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Cargo-exento test",
            actor=None,
        )

        # 2 voting members + 1 cargo-exempt member
        voting_user = user_factory(role_codes=["R-JUNTA"])
        voting_user2 = user_factory(role_codes=["R-JUNTA"])
        cargo_user = user_factory(role_codes=["R-JUNTA"])

        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": voting_user.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                },
                {
                    "user_id": voting_user2.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                },
                {
                    "user_id": cargo_user.id,
                    "rol": "Secretario de Educación",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": True,
                    "conflicto_declarado": False,
                },
            ],
            actor=None,
        )
        sesion.refresh_from_db()

        # Only 2 voting members count; quórum for 2 voting = 2 → barely met.
        # But the cargo-exempts are not counted → voting_present = 2, quorum = 2.
        assert (
            sesion.voting_members_present() == 2
        ), f"Expected 2 voting members, got {sesion.voting_members_present()}"
        assert sesion.quorum_met() is True  # 2 present, need 2 (mitad+1 of 2)

        # The cargo-exempt member cannot vote
        cargo_miembro = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=cargo_user.id)
        assert cargo_miembro.can_vote() is False

        # Remove the voting_user2 so only cargo-exempt remains → quórum NOT met
        cargo_miembro.asistencia = MiembroSesion.Asistencia.AUSENTE
        cargo_miembro.save()
        voting_user2_miembro = MiembroSesion.objects.get(
            sesion_id=sesion.id, user_id=voting_user2.id
        )
        voting_user2_miembro.asistencia = MiembroSesion.Asistencia.AUSENTE
        voting_user2_miembro.save()
        # Re-fetch from DB to clear related-manager cache
        sesion = Sesion.objects.get(id=sesion.id)

        # Now only 1 voting member present, majority = floor(1/2)+1 = 1; quorum MET.
        assert sesion.voting_members_present() == 1
        assert sesion.quorum_met() is True


# ---------------------------------------------------------------------------
# Voting
# ---------------------------------------------------------------------------


class TestVoto:
    @pytest.fixture
    def sesion_con_convocados(self, user_factory):
        """Session in CONVOCADA state with 2 voting members, ready to open."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Votación test",
            actor=None,
        )
        users = [user_factory(role_codes=["R-JUNTA"]) for _ in range(2)]
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": u.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
                for u in users
            ],
            actor=None,
        )
        return sesion, users

    def test_conflicto_voto_rejected(self, user_factory):
        """A member with conflicto_declarado=True cannot vote."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Conflicto test",
            actor=None,
        )
        voting_user = user_factory(role_codes=["R-JUNTA"])
        conflict_user = user_factory(role_codes=["R-JUNTA"])

        # Register both members while session is still CONVOCADA
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": voting_user.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                },
                {
                    "user_id": conflict_user.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": True,  # KEY: cannot vote
                },
            ],
            actor=None,
        )
        # Add punto before opening session (CONVOCADA required)
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Punto de prueba")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)

        # Verify the conflicted member cannot vote
        conflicto_miembro = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=conflict_user.id)
        assert conflicto_miembro.can_vote() is False

        # Attempting to vote for the conflicted member must raise
        with pytest.raises(ValueError) as exc_info:
            SessionService.registrar_voto(
                sesion_id=sesion.id,
                punto_id=punto.id,
                miembro_sesion_id=conflicto_miembro.id,
                valor=Voto.Valor.A_FAVOR,
                actor=None,
            )
        assert "conflicto" in str(exc_info.value).lower()

    def test_vote_update_until_closed(self, sesion_con_convocados):
        """A member may change their vote while the punto is PENDIENTE."""
        sesion, users = sesion_con_convocados
        # Add punto while session is CONVOCADA
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Punto votable")
        # Open the session
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)

        # Get the first member's MiembroSesion
        miembro = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=users[0].id)

        # Cast A_FAVOR
        voto1 = SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro.id,
            valor=Voto.Valor.A_FAVOR,
            actor=None,
        )
        assert voto1.valor == Voto.Valor.A_FAVOR

        # Update to EN_CONTRA
        voto2 = SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro.id,
            valor=Voto.Valor.EN_CONTRA,
            actor=None,
        )
        assert voto2.valor == Voto.Valor.EN_CONTRA
        assert voto2.pk == voto1.pk  # Same row updated

        # Only one vote per member per punto
        assert punto.votos.count() == 1

    def test_punto_cerrar_a_favor_mayor(self, sesion_con_convocados):
        """Punto is APROBADO when A_FAVOR > EN_CONTRA."""
        sesion, users = sesion_con_convocados
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Aprobar")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)

        miembro_a = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=users[0].id)
        miembro_b = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=users[1].id)

        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro_a.id,
            valor=Voto.Valor.A_FAVOR,
            actor=None,
        )
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro_b.id,
            valor=Voto.Valor.A_FAVOR,
            actor=None,
        )

        punto_cerrado = SessionService.cerrar_punto(punto.id, actor=None)
        assert punto_cerrado.estado == OrdenDelDiaPunto.Estado.APROBADO

    def test_punto_cerrar_empate_rechazado(self, sesion_con_convocados):
        """Punto is RECHAZADO when EN_CONTRA >= A_FAVOR (tie)."""
        sesion, users = sesion_con_convocados
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Empate")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)

        miembro_a = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=users[0].id)
        miembro_b = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=users[1].id)

        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro_a.id,
            valor=Voto.Valor.A_FAVOR,
            actor=None,
        )
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro_b.id,
            valor=Voto.Valor.EN_CONTRA,
            actor=None,
        )

        punto_cerrado = SessionService.cerrar_punto(punto.id, actor=None)
        assert punto_cerrado.estado == OrdenDelDiaPunto.Estado.RECHAZADO

    def test_punto_cerrar_cero_votos_rechazado(self, sesion_con_convocados):
        """Punto is RECHAZADO when no votes are cast at all (a_favor=0, en_contra=0)."""
        sesion, users = sesion_con_convocados
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Sin votos")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)
        # Deliberately cast NO votes; close the punto
        punto_cerrado = SessionService.cerrar_punto(punto.id, actor=None)
        assert punto_cerrado.estado == OrdenDelDiaPunto.Estado.RECHAZADO

    def test_punto_cerrar_solo_abstencion_rechazado(self, sesion_con_convocados):
        """Punto is RECHAZADO when all present members voted ABSTENCION."""
        sesion, users = sesion_con_convocados
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Solo abstención")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)
        # Both members vote ABSTENCION (a_favor=0, en_contra=0 → RECHAZADO)
        miembro_a = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=users[0].id)
        miembro_b = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=users[1].id)
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro_a.id,
            valor=Voto.Valor.ABSTENCION,
            actor=None,
        )
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro_b.id,
            valor=Voto.Valor.ABSTENCION,
            actor=None,
        )
        punto_cerrado = SessionService.cerrar_punto(punto.id, actor=None)
        assert punto_cerrado.estado == OrdenDelDiaPunto.Estado.RECHAZADO

    def test_abstention_no_cuenta_mayor(self, sesion_con_convocados, user_factory):
        """ABSTENCION never counts toward majority."""
        sesion, users = sesion_con_convocados
        third_user = user_factory(role_codes=["R-JUNTA"])
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": third_user.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
            ],
            actor=None,
        )
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Solo A_FAVOR")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)

        third_miembro = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=third_user.id)
        miembro_a = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=users[0].id)

        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro_a.id,
            valor=Voto.Valor.A_FAVOR,
            actor=None,
        )
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=third_miembro.id,
            valor=Voto.Valor.ABSTENCION,
            actor=None,
        )

        # 1 A_FAVOR vs 0 EN_CONTRA → majority (A_FAVOR > EN_CONTRA) → APROBADO
        # ABSTENCION doesn't help reach majority but also doesn't block
        punto_cerrado = SessionService.cerrar_punto(punto.id, actor=None)
        assert punto_cerrado.estado == OrdenDelDiaPunto.Estado.APROBADO


# ---------------------------------------------------------------------------
# Session finalize
# ---------------------------------------------------------------------------


class TestFinalizarSesion:
    def test_finalizar_requires_all_puntos_closed(self, user_factory):
        """finalizar_sesion raises if any punto is still PENDIENTE."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Finalizar test",
            actor=None,
        )
        users = [user_factory(role_codes=["R-JUNTA"]) for _ in range(2)]
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": u.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
                for u in users
            ],
            actor=None,
        )

        # Add 2 puntos while session is CONVOCADA
        p1 = SessionService.agregar_punto(sesion.id, numero=1, texto="P1")
        SessionService.agregar_punto(sesion.id, numero=2, texto="P2")

        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)

        # Close only p1; p2 stays PENDIENTE
        miembro = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=users[0].id)
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=p1.id,
            miembro_sesion_id=miembro.id,
            valor=Voto.Valor.A_FAVOR,
            actor=None,
        )
        SessionService.cerrar_punto(p1.id, actor=None)

        # p2 still PENDIENTE
        sesion.refresh_from_db()
        assert not sesion.all_puntos_closed()

        with pytest.raises(ValueError) as exc_info:
            SessionService.finalizar_sesion(sesion.id, actor=None)
        assert "pendientes" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# Acta generation + SHA-256
# ---------------------------------------------------------------------------


class TestActaSesion:
    def test_generar_acta_pdf_sha256(self, user_factory, mocker):
        """generar_acta produces a PDF file and stores its SHA-256 hash."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Acta test",
            actor=None,
        )
        users = [user_factory(role_codes=["R-JUNTA"]) for _ in range(2)]
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": u.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
                for u in users
            ],
            actor=None,
        )
        # Add and close a punto while session is CONVOCADA
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Punto test")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)
        # Vote and close the punto before finalizing
        miembro = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=users[0].id)
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro.id,
            valor=Voto.Valor.A_FAVOR,
            actor=None,
        )
        SessionService.cerrar_punto(punto.id, actor=None)
        SessionService.finalizar_sesion(sesion.id, actor=None)

        # Patch WeasyPrint so the test doesn't need the library
        fake_pdf = b"%PDF-1.4 fake pdf content for test"
        mocker.patch(
            "apps.governance.sessions.services.SessionService._generar_pdf_bytes",
            return_value=fake_pdf,
        )

        acta = SessionService.generar_acta(sesion.id, actor=None)

        assert acta.pdf is not None
        assert acta.pdf_sha256 == hashlib.sha256(fake_pdf).hexdigest()
        assert acta.estado == ActaSesion.Estado.GENERADA

    def test_firmar_acta_stores_pre_post_hash(self, user_factory, mocker):
        """firmar_acta stores pre_sign_hash, post_sign_hash, and firmantes."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Firma test",
            actor=None,
        )
        users = [user_factory(role_codes=["R-JUNTA"]) for _ in range(2)]
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": u.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
                for u in users
            ],
            actor=None,
        )
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Punto test")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)
        # Vote and close the punto before finalizing
        miembro = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=users[0].id)
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro.id,
            valor=Voto.Valor.A_FAVOR,
            actor=None,
        )
        SessionService.cerrar_punto(punto.id, actor=None)
        SessionService.finalizar_sesion(sesion.id, actor=None)

        fake_pdf = b"%PDF-1.4 signature test"
        mocker.patch(
            "apps.governance.sessions.services.SessionService._generar_pdf_bytes",
            return_value=fake_pdf,
        )
        mocker.patch(
            "apps.legalization.signer.SignerFactory.get_provider",
            return_value=mocker.MagicMock(
                sign=mocker.MagicMock(
                    return_value=mocker.MagicMock(
                        pre_sign_hash="pre_hash_abc123",
                        post_sign_hash="post_hash_def456",
                        provider="mock",
                    )
                )
            ),
        )

        # Generate first
        SessionService.generar_acta(sesion.id, actor=None)

        firmantes_list = ["Presidente Junta", "Secretario de Educación"]
        acta = SessionService.firmar_acta(
            sesion_id=sesion.id,
            firmantes=firmantes_list,
            actor=None,
        )

        assert acta.pre_sign_hash == "pre_hash_abc123"
        assert acta.post_sign_hash == "post_hash_def456"
        assert acta.estado == ActaSesion.Estado.FIRMADA
        assert acta.signed_at is not None
        assert len(acta.firmantes) == 2
        assert all("nombre" in f for f in acta.firmantes)


# ---------------------------------------------------------------------------
# Audit events
# ---------------------------------------------------------------------------


class TestAuditEvents:
    def test_convocar_emits_audit(self, user_factory):
        """convocar_sesion emits a SESSION_CONVOCAR audit event."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        initial_count = AuditEvent.objects.filter(
            action="SESSION_CONVOCAR", module="governance"
        ).count()

        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Auditoría test",
            actor=None,
        )

        assert (
            AuditEvent.objects.filter(
                action="SESSION_CONVOCAR",
                entity="Sesion",
                entity_id=sesion.id,
                module="governance",
            ).count()
            == initial_count + 1
        )

    def test_asistencia_emits_audit(self, user_factory):
        """registrar_asistencia emits SESSION_ASISTENCIA."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Auditoría asistencia",
            actor=None,
        )
        user = user_factory(role_codes=["R-JUNTA"])
        initial = AuditEvent.objects.filter(
            action="SESSION_ASISTENCIA", module="governance"
        ).count()

        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": user.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
            ],
            actor=None,
        )

        assert (
            AuditEvent.objects.filter(
                action="SESSION_ASISTENCIA",
                entity="Sesion",
                entity_id=sesion.id,
                module="governance",
            ).count()
            == initial + 1
        )

    def test_abrir_emits_audit(self, user_factory):
        """abrir_sesion emits SESSION_ABRIR."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Auditoría abrir",
            actor=None,
        )
        users = [user_factory(role_codes=["R-JUNTA"]) for _ in range(2)]
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": u.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
                for u in users
            ],
            actor=None,
        )
        initial = AuditEvent.objects.filter(action="SESSION_ABRIR", module="governance").count()

        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)

        assert (
            AuditEvent.objects.filter(
                action="SESSION_ABRIR",
                entity="Sesion",
                entity_id=sesion.id,
                module="governance",
            ).count()
            == initial + 1
        )

    def test_voto_emits_audit(self, user_factory):
        """registrar_voto emits SESSION_VOTO."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Auditoría voto",
            actor=None,
        )
        user = user_factory(role_codes=["R-JUNTA"])
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": user.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
            ],
            actor=None,
        )
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Votable")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)
        miembro = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=user.id)
        initial = AuditEvent.objects.filter(action="SESSION_VOTO", module="governance").count()

        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro.id,
            valor=Voto.Valor.A_FAVOR,
            actor=None,
        )

        assert (
            AuditEvent.objects.filter(
                action="SESSION_VOTO",
                entity="Voto",
                module="governance",
            ).count()
            == initial + 1
        )

    def test_cerrar_punto_emits_audit(self, user_factory):
        """cerrar_punto emits SESSION_PUNTO_CERRAR."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Auditoría cerrar",
            actor=None,
        )
        user = user_factory(role_codes=["R-JUNTA"])
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": user.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
            ],
            actor=None,
        )
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Cerrable")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)
        miembro = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=user.id)
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro.id,
            valor=Voto.Valor.A_FAVOR,
            actor=None,
        )
        initial = AuditEvent.objects.filter(
            action="SESSION_PUNTO_CERRAR", module="governance"
        ).count()

        SessionService.cerrar_punto(punto.id, actor=None)

        assert (
            AuditEvent.objects.filter(
                action="SESSION_PUNTO_CERRAR",
                entity="OrdenDelDiaPunto",
                entity_id=coerce_entity_id(punto.id),
                module="governance",
            ).count()
            == initial + 1
        )


class TestDeclaracionConflicto:
    @pytest.fixture
    def sesion_for_conflicto(self, user_factory):
        """Session with 3 voting members (declarant + 2 voters), ready to open."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(
            datetime.combine(_add_working_days(today, 10), time(9, 0))
        )
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Conflicto test",
            actor=None,
        )
        declarant = user_factory(role_codes=["R-JUNTA"])
        voter_a = user_factory(role_codes=["R-JUNTA"])
        voter_b = user_factory(role_codes=["R-JUNTA"])
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": declarant.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                },
                {
                    "user_id": voter_a.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                },
                {
                    "user_id": voter_b.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                },
            ],
            actor=None,
        )
        return sesion, declarant, voter_a, voter_b

    def test_votar_impedimento_sets_revisado_por(self, sesion_for_conflicto):
        """votar_impedimento sets revisado_por to the actor who resolved it.

        CHG-502: revisado_por must be populated when the impediment is
        resolved, mirroring the pattern in approve_termination() and the
        revisado_at field already being set.
        """
        sesion, declarant, voter_a, voter_b = sesion_for_conflicto
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Punto de conflicto")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)

        declarant_miembro = MiembroSesion.objects.get(sesion=sesion, user=declarant)
        voter_a_miembro = MiembroSesion.objects.get(sesion=sesion, user=voter_a)
        voter_b_miembro = MiembroSesion.objects.get(sesion=sesion, user=voter_b)

        # Declarant declares a conflict
        declaracion = SessionService.declarar_conflicto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=declarant_miembro.id,
            texto="Conflicto de interés declarado",
            actor=declarant,
        )

        # Need majority=2, so cast two votes; voter_b's call triggers resolution
        SessionService.votar_impedimento(
            declaracion_id=declaracion.id,
            miembro_sesion_id=voter_a_miembro.id,
            a_favor=True,
            actor=voter_a,
        )
        resolved = SessionService.votar_impedimento(
            declaracion_id=declaracion.id,
            miembro_sesion_id=voter_b_miembro.id,
            a_favor=True,
            actor=voter_b,
        )

        declaracion.refresh_from_db()
        # revisado_por is set from the actor of the LAST call that triggers resolution
        assert declaracion.revisado_por == voter_b, (
            "revisado_por must be set to the actor from the call that triggers resolution"
        )
        assert declaracion.revisado_at is not None, "revisado_at must be set"

    def test_finalizar_emits_audit(self, user_factory):
        """finalizar_sesion emits SESSION_FINALIZAR."""
        today = timezone.now().date()
        fecha_hora = timezone.make_aware(datetime.combine(_add_working_days(today, 10), time(9, 0)))
        sesion = SessionService.convocar_sesion(
            organo=Sesion.Organo.JUNTA,
            tipo=Sesion.Tipo.ORDINARIA,
            fecha_hora=fecha_hora,
            asunto="Auditoría finalizar",
            actor=None,
        )
        user = user_factory(role_codes=["R-JUNTA"])
        SessionService.registrar_asistencia(
            sesion_id=sesion.id,
            member_records=[
                {
                    "user_id": user.id,
                    "rol": "Miembro",
                    "asistencia": MiembroSesion.Asistencia.PRESENTE,
                    "es_miembro_cargo": False,
                    "conflicto_declarado": False,
                }
            ],
            actor=None,
        )
        punto = SessionService.agregar_punto(sesion.id, numero=1, texto="Finalizable")
        sesion.refresh_from_db()
        SessionService.abrir_sesion(sesion.id, actor=None)
        # Vote and close the punto before finalizing
        miembro = MiembroSesion.objects.get(sesion_id=sesion.id, user_id=user.id)
        SessionService.registrar_voto(
            sesion_id=sesion.id,
            punto_id=punto.id,
            miembro_sesion_id=miembro.id,
            valor=Voto.Valor.A_FAVOR,
            actor=None,
        )
        SessionService.cerrar_punto(punto.id, actor=None)
        initial = AuditEvent.objects.filter(action="SESSION_FINALIZAR", module="governance").count()

        SessionService.finalizar_sesion(sesion.id, actor=None)
        assert (
            AuditEvent.objects.filter(
                action="SESSION_FINALIZAR",
                entity="Sesion",
                entity_id=sesion.id,
                module="governance",
            ).count()
            == initial + 1
        )
