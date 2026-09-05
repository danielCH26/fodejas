"""Tests for PDF generation service (CHG-207)."""
import hashlib
import pytest
from django.test import TestCase
from django.utils import timezone
from unittest.mock import patch, MagicMock

from apps.governance.models import ActoAdministrativo
from apps.governance.services.pdf import generar_pdf_acto, guardar_pdf_acto


class TestGenerarPdfActo(TestCase):
    """Tests for generar_pdf_acto function."""

    def setUp(self):
        """Set up test data."""
        self.acto = ActoAdministrativo.objects.create(
            numero="FODEJAS-2026-00001",
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion=timezone.now().date(),
            asunto="Test act subject",
            resolutivo="Test resolutive content",
            considerandos=["Considerando 1", "Considerando 2"],
            estado=ActoAdministrativo.Estado.BORRADOR,
        )

    def test_generar_pdf_retorna_bytes(self):
        """Test that generar_pdf_acto returns PDF bytes."""
        try:
            from weasyprint import HTML
            pdf_bytes = generar_pdf_acto(self.acto)
            self.assertIsInstance(pdf_bytes, bytes)
            self.assertGreater(len(pdf_bytes), 0)
        except ImportError:
            # WeasyPrint not installed, skip test
            self.skipTest("WeasyPrint not installed")

    @patch("apps.governance.services.pdf.get_template")
    def test_generar_pdf_usa_template(self, mock_get_template):
        """Test that generar_pdf_acto uses the correct template."""
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>test</html>"
        mock_get_template.return_value = mock_template

        try:
            generar_pdf_acto(self.acto)
            mock_get_template.assert_called()
        except ImportError:
            self.skipTest("WeasyPrint not installed")


class TestGuardarPdfActo(TestCase):
    """Tests for guardar_pdf_acto function."""

    def setUp(self):
        """Set up test data."""
        self.acto = ActoAdministrativo.objects.create(
            numero="FODEJAS-2026-00002",
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion=timezone.now().date(),
            asunto="Test act subject",
            resolutivo="Test resolutive content",
            estado=ActoAdministrativo.Estado.BORRADOR,
        )

    def test_guardar_pdf_calcula_sha256(self):
        """Test that guardar_pdf_acto calculates SHA-256 hash."""
        try:
            from weasyprint import HTML
            sha256 = guardar_pdf_acto(self.acto)

            # Should be a valid SHA-256 hash
            self.assertIsNotNone(sha256)
            self.assertEqual(len(sha256), 64)  # SHA-256 = 64 hex chars

            # Verify it's stored in the acto
            self.acto.refresh_from_db()
            self.assertEqual(self.acto.pdf_sha256, sha256)
        except ImportError:
            self.skipTest("WeasyPrint not installed")

    def test_guardar_pdf_guarda_archivo(self):
        """Test that guardar_pdf_acto saves the PDF file."""
        try:
            from weasyprint import HTML
            sha256 = guardar_pdf_acto(self.acto)

            # Verify file was saved
            self.acto.refresh_from_db()
            self.assertIsNotNone(self.acto.pdf)
            self.assertTrue(self.acto.pdf.name.endswith(".pdf"))
        except ImportError:
            self.skipTest("WeasyPrint not installed")

    def test_guardar_pdf_retorna_sha256(self):
        """Test that guardar_pdf_acto returns the SHA-256 hash."""
        try:
            from weasyprint import HTML
            sha256 = guardar_pdf_acto(self.acto)

            # Verify returned value matches stored hash
            self.acto.refresh_from_db()
            self.assertEqual(sha256, self.acto.pdf_sha256)
        except ImportError:
            self.skipTest("WeasyPrint not installed")
