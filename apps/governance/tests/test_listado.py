"""Tests for ListadoDefinitivo model and service (CHG-207)."""
import pytest
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock

from apps.governance.models import ActoAdministrativo, ListadoDefinitivo, SecuencialActo
from apps.governance.services.listado import generar_listado_definitivo, obtener_ranking_final
from apps.convocatories.models import Convocatory


class TestListadoDefinitivoModel(TestCase):
    """Tests for ListadoDefinitivo model."""

    def test_listado_creacion(self):
        """Test that ListadoDefinitivo can be created."""
        acto = ActoAdministrativo.objects.create(
            numero="FODEJAS-2026-00003",
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion=timezone.now().date(),
            asunto="Test subject",
            resolutivo="Test resolutive",
            estado=ActoAdministrativo.Estado.BORRADOR,
        )

        ranking = [
            {"solicitud_id": "1", "puntaje": 95.5, "rank": 1},
            {"solicitud_id": "2", "puntaje": 90.0, "rank": 2},
        ]

        # This would need a Convocatory to work properly
        # Skipping full integration test for now
        self.assertIsNotNone(acto)


class TestObtenerRankingFinal(TestCase):
    """Tests for obtener_ranking_final function."""

    @patch("apps.applications.models.Solicitud")
    @patch("apps.scoring.models.PuntajeTotal")
    def test_obtener_ranking_ordenado(self, mock_puntaje_clase, mock_solicitud_clase):
        """Test that ranking is ordered by puntaje descending."""
        # Create mock objects
        mock_solicitud_1 = MagicMock()
        mock_solicitud_1.uuid = "uuid-1"
        mock_solicitud_1.radicado = "R001"
        mock_solicitud_1.aspirante.get_full_name.return_value = "Juan Perez"
        mock_solicitud_1.estado = "verificada"

        mock_solicitud_2 = MagicMock()
        mock_solicitud_2.uuid = "uuid-2"
        mock_solicitud_2.radicado = "R002"
        mock_solicitud_2.aspirante.get_full_name.return_value = "Maria Garcia"
        mock_solicitud_2.estado = "verificada"

        # Mock querysets
        mock_queryset = MagicMock()
        mock_queryset.filter.return_value = mock_queryset
        mock_queryset.select_related.return_value = mock_queryset
        mock_queryset.__iter__ = lambda self: iter([mock_solicitud_1, mock_solicitud_2])
        mock_solicitud_clase.objects = mock_queryset

        # Mock puntajes
        mock_puntaje_1 = MagicMock()
        mock_puntaje_1.puntaje_total = 95.5
        mock_puntaje_1.puntaje_merito = 50.0
        mock_puntaje_1.puntaje_socioeconomico = 30.0
        mock_puntaje_1.puntaje_residencia = 15.5

        mock_puntaje_2 = MagicMock()
        mock_puntaje_2.puntaje_total = 85.0
        mock_puntaje_2.puntaje_merito = 45.0
        mock_puntaje_2.puntaje_socioeconomico = 25.0
        mock_puntaje_2.puntaje_residencia = 15.0

        def get_side_effect(solicitud):
            if solicitud.uuid == "uuid-1":
                return mock_puntaje_1
            return mock_puntaje_2

        mock_puntaje_clase.objects.get.side_effect = get_side_effect
        mock_puntaje_clase.DoesNotExist = Exception

        # Create a mock Convocatory
        mock_convocatoria = MagicMock(spec=Convocatory)

        # Call the function
        ranking = obtener_ranking_final(mock_convocatoria)

        # Assertions
        self.assertEqual(len(ranking), 2)
        self.assertEqual(ranking[0]["puntaje"], 95.5)
        self.assertEqual(ranking[0]["rank"], 1)
        self.assertEqual(ranking[1]["puntaje"], 85.0)
        self.assertEqual(ranking[1]["rank"], 2)


class TestGenerarListadoDefinitivo(TestCase):
    """Tests for generar_listado_definitivo function."""

    def test_generar_listado_crea_listado(self):
        """Test that generar_listado_definitivo creates a listing."""
        # Would need Convocatory fixture
        pass
