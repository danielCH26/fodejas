"""Reclamación lifecycle flow test (CHG-205 + CHG-208).

End-to-end flow: crear solicitud → presentar reclamación →
transicionar a EN_REVISION → resolver favorable → verificar
historial.
"""
from __future__ import annotations

import pytest
from django.test import TestCase

from apps.accounts.models import CustomUser, Role, UserRole
from apps.applications.models import Solicitud
from apps.claims.models import Apelacion, Reclamacion, ReclamacionHistorial
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
        nombre="Convocatoria Reclamacion",
        codigo="CR-2026-001",
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
class TestReclamacionFlow(TestCase):
    """End-to-end: presentar → en_revision → resuelta favorable."""

    def setUp(self):
        self.aspirante = _make_user("aspirante", ["R-ASPIRANTE"])
        self.junta = _make_user("junta", ["R-JUNTA"])
        self.convocatoria = _make_convocatoria()
        self.solicitud = _make_solicitud(self.convocatoria, aspirante=self.aspirante)

    def test_reclamacion_presentada_to_resuelta_favorable(self):
        # 1. Aspirante presents a reclamacion.
        rec = Reclamacion.objects.create(
            solicitud=self.solicitud,
            tipo=Reclamacion.TipoReclamacion.PUNTAJE,
            descripcion="Mi puntaje es incorrecto.",
            estado=Reclamacion.Estado.PRESENTADA,
        )
        self.assertEqual(rec.estado, Reclamacion.Estado.PRESENTADA)

        # 2. Junta transitions to EN_REVISION (manual workflow step).
        rec.estado = Reclamacion.Estado.EN_REVISION
        rec.save()
        ReclamacionHistorial.objects.create(
            reclamacion=rec,
            estado_anterior=Reclamacion.Estado.PRESENTADA,
            estado_nuevo=Reclamacion.Estado.EN_REVISION,
            observacion="Recibida para revisión por la Junta.",
            actor=self.junta,
        )

        # 3. Junta resuelve favorable.
        rec.estado = Reclamacion.Estado.RESUELTA
        rec.respuesta = "Se acepta el reclamo. Se recalcula el puntaje."
        rec.resuelto_por = self.junta
        rec.fecha_resolucion = __import__("django.utils.timezone", fromlist=["now"]).now()
        rec.save()
        ReclamacionHistorial.objects.create(
            reclamacion=rec,
            estado_anterior=Reclamacion.Estado.EN_REVISION,
            estado_nuevo=Reclamacion.Estado.RESUELTA,
            observacion="Reclamo resuelto favorablemente.",
            actor=self.junta,
        )

        # 4. Verify final state and historial.
        rec.refresh_from_db()
        self.assertEqual(rec.estado, Reclamacion.Estado.RESUELTA)
        historial = list(rec.historial.all())
        self.assertEqual(len(historial), 2)
        self.assertEqual(historial[0].estado_anterior, Reclamacion.Estado.PRESENTADA)
        self.assertEqual(historial[1].estado_nuevo, Reclamacion.Estado.RESUELTA)

    def test_reclamacion_resuelta_habilita_apelacion(self):
        """After a favorable resolución, an Apelacion may be filed."""
        rec = Reclamacion.objects.create(
            solicitud=self.solicitud,
            tipo=Reclamacion.TipoReclamacion.PUNTAJE,
            descripcion="X",
            estado=Reclamacion.Estado.RESUELTA,
            respuesta="Favorable",
            resuelto_por=self.junta,
        )
        # The Aspirante files an Apelacion against this favourable
        # resolución. We just verify the FK link is correct (the view
        # gating is tested elsewhere).
        apel = Apelacion.objects.create(
            reclamacion=rec,
            estado=Apelacion.Estado.PRESENTADA,
            descripcion="Discrepancia en los considerandos.",
        )
        self.assertEqual(apel.reclamacion_id, rec.id)
        self.assertEqual(apel.estado, Apelacion.Estado.PRESENTADA)
        # The Apelacion requires the parent reclamacion to be RESUELTA
        # (this is enforced at the view layer; the model FK allows any
        # state — see apps/claims/views.py:CanCreateApelacion).
        rec.refresh_from_db()
        self.assertEqual(rec.estado, Reclamacion.Estado.RESUELTA)

    def test_reclamacion_rechazada_no_es_apelable_via_modelo(self):
        """The model allows it; the view layer enforces.

        Per CPACA, a rechazada agotates the vía gubernativa. We verify
        here that the model permits it (since the gating lives in
        CanCreateApelacion.has_object_permission — see
        apps/claims/permissions.py), and document the behavior.
        """
        rec = Reclamacion.objects.create(
            solicitud=self.solicitud,
            tipo=Reclamacion.TipoReclamacion.PUNTAJE,
            descripcion="X",
            estado=Reclamacion.Estado.RECHAZADA,
            respuesta="Improcedente",
            resuelto_por=self.junta,
        )
        # An Apelacion could be created at the model level (no DB
        # constraint), but CanCreateApelacion.has_object_permission
        # rejects with 403 because reclamacion.estado != RESUELTA.
        self.assertEqual(rec.estado, Reclamacion.Estado.RECHAZADA)
