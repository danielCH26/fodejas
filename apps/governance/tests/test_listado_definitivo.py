"""Tests for AUD-005 fix: governance listado uses real ``PuntajeTotal`` fields
and transitions ``Convocatory`` to ``DEFINITIVA``.
"""
from decimal import Decimal
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.applications.models import Solicitud
from apps.convocatories.models import Convocatory
from apps.governance.services.listado import (
    generar_listado_definitivo,
    obtener_ranking_final,
)
from apps.scoring.models import PuntajeTotal

User = get_user_model()


class ListadoDefinitivoTest(TestCase):
    """AUD-005 — generar_listado_definitivo must not raise ``AttributeError``."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="aspirante@example.com",
            documento="1234567890",
            first_name="Aspirante",
            last_name="Ejemplo",
            password="testpass123",
        )
        self.convocatoria = Convocatory.objects.create(
            nombre="Convocatoria Test",
            codigo="test-2026",
            periodo="2026-1",
            estado=Convocatory.Estado.EN_CALIFICACION,
        )
        self.solicitud = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user,
            estado=Solicitud.Estado.VERIFICADA,
            radicado="FODEJAS-2026-AUD005",
        )

    def test_generar_listado_definitivo_no_attribute_error(self):
        """Calling ``generar_listado_definitivo`` does not raise."""
        # Stub ``ListadoDefinitivo`` so the test does not depend on a
        # governance model migration: we are asserting that the
        # Convocatory state-transition path is reached with the real
        # ``DEFINITIVA`` enum.
        from apps.governance.models import ListadoDefinitivo

        original_create = ListadoDefinitivo.objects.create
        captured = {}

        def fake_create(**kwargs):
            captured.update(kwargs)
            listado = MagicMock()
            listado.convocatoria = kwargs["convocatoria"]
            return listado

        ListadoDefinitivo.objects.create = fake_create
        try:
            acto = MagicMock()
            resultado = generar_listado_definitivo(
                self.convocatoria,
                acto,
                ranking_data=[{"solicitud_id": "abc", "puntaje": 1, "rank": 1}],
            )
        finally:
            ListadoDefinitivo.objects.create = original_create

        self.assertIsNotNone(resultado)
        # The convocatoria MUST end in DEFINITIVA after the call.
        self.convocatoria.refresh_from_db()
        self.assertEqual(self.convocatoria.estado, Convocatory.Estado.DEFINITIVA)

    def test_obtener_ranking_final_uses_real_puntaje_fields(self):
        """obtener_ranking_final reads only real ``PuntajeTotal`` fields."""
        # Create a PuntajeTotal with the real field names.
        PuntajeTotal.objects.create(
            solicitud=self.solicitud,
            puntaje_socioeconomico=Decimal("40.00"),
            puntaje_academico=Decimal("30.00"),
            puntaje_excelencia=Decimal("20.00"),
            puntaje_total=Decimal("90.00"),
            calculado_por=self.user,
        )

        ranking = obtener_ranking_final(self.convocatoria)

        self.assertEqual(len(ranking), 1)
        detallado = ranking[0]["puntaje_detallado"]
        # CHG-805 AUD-005: the payload uses the real field names.
        self.assertIn("excelencia", detallado)
        self.assertIn("academico", detallado)
        self.assertIn("socioeconomico", detallado)
        # The legacy keys MUST NOT appear.
        self.assertNotIn("merito", detallado)
        self.assertNotIn("residencia", detallado)

        # And the values come from the real fields.
        self.assertEqual(detallado["excelencia"], Decimal("20.00"))
        self.assertEqual(detallado["academico"], Decimal("30.00"))
        self.assertEqual(detallado["socioeconomico"], Decimal("40.00"))

    def test_obtener_ranking_falta_puntaje_no_attribute_error(self):
        """Solicitudes without PuntajeTotal get a zeroed payload (no crash)."""
        ranking = obtener_ranking_final(self.convocatoria)
        self.assertEqual(len(ranking), 1)
        detallado = ranking[0]["puntaje_detallado"]
        # No legacy keys, and all real keys map to Decimal('0').
        self.assertEqual(detallado["excelencia"], 0)
        self.assertEqual(detallado["academico"], 0)
        self.assertEqual(detallado["socioeconomico"], 0)
        self.assertNotIn("merito", detallado)
        self.assertNotIn("residencia", detallado)
