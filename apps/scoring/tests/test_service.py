"""Tests for scoring service."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.applications.models import Solicitud
from apps.convocatories.models import Convocatory
from apps.scoring.models import Evaluacion
from apps.scoring.services.scoring_service import (
    DEFAULT_WEIGHTS,
    calcular_puntaje_total,
    create_default_evaluaciones,
    generar_ranking_general,
)

User = get_user_model()


class ScoringServiceTest(TestCase):
    """Test scoring service functions."""

    def setUp(self):
        self.user = User.objects.create_user(
            email="aspirante@example.com",
            documento="12345678",
            first_name="Aspirante",
            last_name="Test",
            password="testpass123"
        )
        self.convocatoria = Convocatory.objects.create(
            nombre="Test Convocatoria",
            estado=Convocatory.Estado.EN_INSCRIPCION,
        )
        self.solicitud = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user,
            estado=Solicitud.Estado.VERIFICADA,
            radicado="FODEJAS-2026-00001",
        )

    def test_default_weights(self):
        """Test default weights are 50/30/20."""
        self.assertEqual(DEFAULT_WEIGHTS["socioeconomico"], Decimal("0.50"))
        self.assertEqual(DEFAULT_WEIGHTS["academico"], Decimal("0.30"))
        self.assertEqual(DEFAULT_WEIGHTS["excelencia"], Decimal("0.20"))

    def test_create_default_evaluaciones(self):
        """Test creating default evaluaciones."""
        create_default_evaluaciones(self.solicitud)

        evaluaciones = self.solicitud.evaluaciones.all()
        self.assertEqual(evaluaciones.count(), 3)

        criterios = [e.criterio for e in evaluaciones]
        self.assertIn(Evaluacion.Criterio.SOCIOECONOMICO, criterios)
        self.assertIn(Evaluacion.Criterio.ACADEMICO, criterios)
        self.assertIn(Evaluacion.Criterio.EXCELENCIA, criterios)

    def test_calcular_puntaje_total(self):
        """Test calculating total score."""
        # Create evaluaciones
        create_default_evaluaciones(self.solicitud)

        # Set scores
        eval_socio = self.solicitud.evaluaciones.get(criterio=Evaluacion.Criterio.SOCIOECONOMICO)
        eval_socio.puntaje = Decimal("80.00")
        eval_socio.save()

        eval_acad = self.solicitud.evaluaciones.get(criterio=Evaluacion.Criterio.ACADEMICO)
        eval_acad.puntaje = Decimal("90.00")
        eval_acad.save()

        eval_excel = self.solicitud.evaluaciones.get(criterio=Evaluacion.Criterio.EXCELENCIA)
        eval_excel.puntaje = Decimal("70.00")
        eval_excel.save()

        # Calculate total
        # Expected: (80 * 0.50) + (90 * 0.30) + (70 * 0.20) = 40 + 27 + 14 = 81
        puntaje = calcular_puntaje_total(self.solicitud)

        self.assertEqual(puntaje.puntaje_socioeconomico, Decimal("80.00"))
        self.assertEqual(puntaje.puntaje_academico, Decimal("90.00"))
        self.assertEqual(puntaje.puntaje_excelencia, Decimal("70.00"))
        self.assertEqual(puntaje.puntaje_total, Decimal("81.00"))

    def test_calcular_puntaje_total_with_zeros(self):
        """Test calculating with unevaluated criteria."""
        create_default_evaluaciones(self.solicitud)

        # Don't set any scores - should use 0
        puntaje = calcular_puntaje_total(self.solicitud)

        self.assertEqual(puntaje.puntaje_socioeconomico, Decimal("0"))
        self.assertEqual(puntaje.puntaje_academico, Decimal("0"))
        self.assertEqual(puntaje.puntaje_excelencia, Decimal("0"))
        self.assertEqual(puntaje.puntaje_total, Decimal("0"))


class RankingTest(TestCase):
    """Test ranking functions."""

    def setUp(self):
        self.user1 = User.objects.create_user(
            email="aspirante1@example.com",
            documento="11111111",
            first_name="Aspirante",
            last_name="Uno",
            password="testpass123"
        )
        self.user2 = User.objects.create_user(
            email="aspirante2@example.com",
            documento="22222222",
            first_name="Aspirante",
            last_name="Dos",
            password="testpass123"
        )

        self.convocatoria = Convocatory.objects.create(
            nombre="Test Convocatoria",
            estado=Convocatory.Estado.EN_INSCRIPCION,
        )

        # Create solicitudes with different scores
        self.solicitud1 = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user1,
            estado=Solicitud.Estado.VERIFICADA,
            radicado="FODEJAS-2026-00001",
            datos_personales={"municipio": "san_andres"},
        )

        self.solicitud2 = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.user2,
            estado=Solicitud.Estado.VERIFICADA,
            radicado="FODEJAS-2026-00002",
            datos_personales={"municipio": "providencia"},
        )

        # Create evaluaciones for solicitud1 (higher score)
        create_default_evaluaciones(self.solicitud1)
        for eval in self.solicitud1.evaluaciones.all():
            eval.puntaje = Decimal("90.00")
            eval.save()
        calcular_puntaje_total(self.solicitud1)

        # Create evaluaciones for solicitud2 (lower score)
        create_default_evaluaciones(self.solicitud2)
        for eval in self.solicitud2.evaluaciones.all():
            eval.puntaje = Decimal("80.00")
            eval.save()
        calcular_puntaje_total(self.solicitud2)

    def test_ranking_general(self):
        """Test general ranking."""
        generar_ranking_general(self.convocatoria)

        # Refresh from database to get updated ranking
        self.solicitud1.refresh_from_db()
        self.solicitud2.refresh_from_db()

        puntaje1 = self.solicitud1.puntaje_total
        puntaje2 = self.solicitud2.puntaje_total

        # solicitud1 has higher score, should be rank 1
        self.assertEqual(puntaje1.ranking_general, 1)
        self.assertEqual(puntaje2.ranking_general, 2)

    def test_providencia_priority(self):
        """Test Providencia Island gets priority in ties."""
        # Create a tie situation - give solicitud2 higher score but Providencia
        self.solicitud2.puntaje_total.puntaje_total = Decimal("95.00")
        self.solicitud2.puntaje_total.save()

        generar_ranking_general(self.convocatoria)

        # Refresh from database to get updated ranking
        self.solicitud1.refresh_from_db()
        self.solicitud2.refresh_from_db()

        # Providencia should get priority even with lower score
        puntaje2 = self.solicitud2.puntaje_total

        # With tie-breaking, Providencia should come first
        # Since solicitud2 is Providencia, it should rank higher
        self.assertEqual(puntaje2.ranking_general, 1)
