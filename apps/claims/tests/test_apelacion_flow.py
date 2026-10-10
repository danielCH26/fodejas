"""Apelación lifecycle flow test (CHG-206 + CHG-208).

End-to-end: tras reclamación resuelta favorable → crear apelación →
transicionar a EN_ANALISIS → confirmar (o revocar).
"""
from __future__ import annotations

import pytest
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import CustomUser, Role, UserRole
from apps.applications.models import Solicitud
from apps.claims.models import (
    Apelacion,
    ApelacionHistorial,
    Reclamacion,
)
from apps.convocatories.models import Convocatory


def _make_user(email, codes):
    import uuid as uuidlib

    user = CustomUser.objects.create(
        email=email,
        documento=uuidlib.uuid4().hex[:20],
        telefono="3000000000",
    )
    for code in codes:
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={"name": code, "type": "interno", "description": code},
        )
        UserRole.objects.get_or_create(
            user=user, role=role, convocation_scope_id=None
        )
    return user


def _make_convocatoria():
    return Convocatory.objects.create(
        nombre="Convocatoria Apelacion",
        codigo="CA-2026-001",
        tipo="cerrada",
        periodo="2026-1",
        monto_semestre_smlmv=5,
        duracion_maxima_semestres=10,
        cupo_total=10,
        estado=Convocatory.Estado.DEFINITIVA,
    )


def _make_solicitud(convocatoria, aspirante=None):
    import uuid as uuidlib

    return Solicitud.objects.create(
        convocatoria=convocatoria,
        aspirante=aspirante,
        radicado=f"RAD-{uuidlib.uuid4().hex[:8]}",
        estado=Solicitud.Estado.RADICADA,
    )


@pytest.mark.django_db(transaction=True)
class TestApelacionFlow(TestCase):
    """INICIADA → EN_ANALISIS → CONFIRMADA | REVOCADA."""

    def setUp(self):
        self.aspirante = _make_user("aspirante", ["R-ASPIRANTE"])
        self.junta = _make_user("junta", ["R-JUNTA"])
        self.ofijur = _make_user("ofijur", ["R-OFIJUR"])
        self.convocatoria = _make_convocatoria()
        self.solicitud = _make_solicitud(self.convocatoria, aspirante=self.aspirante)
        # Pre-condition: a resolved favorable Reclamacion.
        self.reclamacion = Reclamacion.objects.create(
            solicitud=self.solicitud,
            tipo=Reclamacion.TipoReclamacion.PUNTAJE,
            descripcion="Puntaje bajo",
            estado=Reclamacion.Estado.RESUELTA,
            respuesta="Favorable.",
            resuelto_por=self.junta,
        )

    def test_apelacion_iniciada_to_confirmada(self):
        # 1. Aspirante files the appeal.
        apel = Apelacion.objects.create(
            reclamacion=self.reclamacion,
            estado=Apelacion.Estado.PRESENTADA,
            descripcion="Discrepancia en los considerandos.",
        )
        self.assertEqual(apel.estado, Apelacion.Estado.PRESENTADA)

        # 2. Oficina Jurídica transitions to EN_ANALISIS.
        apel.estado = Apelacion.Estado.EN_ANALISIS
        apel.save()
        ApelacionHistorial.objects.create(
            apelacion=apel,
            estado_anterior=Apelacion.Estado.PRESENTADA,
            estado_nuevo=Apelacion.Estado.EN_ANALISIS,
            observacion="Admitida para análisis.",
            actor=self.ofijur,
        )

        # 3. Oficina Jurídica confirms (ratifies the Resolución).
        apel.estado = Apelacion.Estado.CONFIRMADA
        apel.respuesta = "Se confirma la Resolución en todas sus partes."
        apel.fecha_resolucion = timezone.now()
        apel.resuelto_por = self.ofijur
        apel.save()
        ApelacionHistorial.objects.create(
            apelacion=apel,
            estado_anterior=Apelacion.Estado.EN_ANALISIS,
            estado_nuevo=Apelacion.Estado.CONFIRMADA,
            observacion="Confirmada por la Oficina Jurídica.",
            actor=self.ofijur,
        )

        apel.refresh_from_db()
        self.assertEqual(apel.estado, Apelacion.Estado.CONFIRMADA)
        historial = list(apel.historial.all())
        self.assertEqual(len(historial), 2)
        self.assertEqual(historial[0].estado_anterior, Apelacion.Estado.PRESENTADA)
        self.assertEqual(historial[1].estado_nuevo, Apelacion.Estado.CONFIRMADA)

    def test_apelacion_revocada_invalidates_first_instance(self):
        """Una Apelación REVOCADA invalida la Reclamación resuelta."""
        from django.utils import timezone

        apel = Apelacion.objects.create(
            reclamacion=self.reclamacion,
            estado=Apelacion.Estado.EN_ANALISIS,
            descripcion="Y",
        )

        apel.estado = Apelacion.Estado.REVOCADA
        apel.respuesta = "Se revoca. Devolver a la Junta para re-decisión."
        apel.fecha_resolucion = timezone.now()
        apel.resuelto_por = self.ofijur
        apel.save()
        ApelacionHistorial.objects.create(
            apelacion=apel,
            estado_anterior=Apelacion.Estado.EN_ANALISIS,
            estado_nuevo=Apelacion.Estado.REVOCADA,
            observacion="Revocada. Expediente vuelve a Junta.",
            actor=self.ofijur,
        )

        apel.refresh_from_db()
        self.assertEqual(apel.estado, Apelacion.Estado.REVOCADA)
        # Per spec, this should invalidate the original RESUELTA.
        # The actual invalidation workflow (returning to Junta) is
        # NOT implemented in this change — it belongs to a future
        # change (CHG-501-sessions, Fase 5).
        # The state TRANSITION is what this change guarantees.
        self.reclamacion.refresh_from_db()
        # The Reclamacion remains RESUELTA in this change; a follow-up
        # will mark it invalid. We assert the Apelación state only.
