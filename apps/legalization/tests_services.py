"""Tests for the legalization service."""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.legalization.models import LegalDocument, LegalizationProcess
from apps.legalization.services import LegalizationService


class TestLegalizationService(TestCase):
    """Tests for LegalizationService."""

    def setUp(self):
        """Set up test data."""
        User = get_user_model()
        self.user = User.objects.create_user(
            email="test@example.com",
            password="testpass123",
            documento="12345678",
        )
        self.convocatoria = MagicMock()
        self.convocatoria.id = "test-conv-123"

    @patch("apps.legalization.services.sign_bytes")
    def test_create_process_for_beneficiary(self, mock_sign):
        """Test creating a legalization process."""
        mock_sign.return_value = MagicMock(
            pre_sign_hash="abc123",
            post_sign_hash="def456",
        )

        process = LegalizationService.create_process_for_beneficiary(self.user, self.convocatoria)

        self.assertEqual(process.beneficiary, self.user)
        self.assertEqual(process.convocatoria, self.convocatoria)
        self.assertEqual(process.status, LegalizationProcess.Status.PENDIENTE)

        # Check documents were created
        docs = process.documents.all()
        self.assertEqual(docs.count(), 3)  # 3 document types

    @patch("apps.legalization.services.sign_bytes")
    def test_sign_document(self, mock_sign):
        """Test signing a document."""
        # Create process and document
        process = LegalizationProcess.objects.create(
            beneficiary=self.user,
            convocatoria=self.convocatoria,
        )
        document = LegalDocument.objects.create(
            process=process,
            document_type=LegalDocument.DocumentType.PAGARE,
        )

        # Mock signature result
        mock_sign.return_value = MagicMock(
            pre_sign_hash="abc123",
            post_sign_hash="def456",
        )

        # Sign document
        result = LegalizationService.sign_document(document)

        self.assertEqual(result.status, LegalDocument.Status.FIRMADO)
        self.assertEqual(result.pre_sign_hash, "abc123")
        self.assertEqual(result.post_sign_hash, "def456")
        self.assertIsNotNone(result.signed_at)

    @patch("apps.legalization.services.sign_bytes")
    def test_sign_invalid_status(self, mock_sign):
        """Test signing a document that's not in PENDIENTE status."""
        mock_sign.return_value = MagicMock(
            pre_sign_hash="abc123",
            post_sign_hash="def456",
        )

        process = LegalizationProcess.objects.create(
            beneficiary=self.user,
            convocatoria=self.convocatoria,
        )
        document = LegalDocument.objects.create(
            process=process,
            document_type=LegalDocument.DocumentType.PAGARE,
            status=LegalDocument.Status.FIRMADO,
        )

        with self.assertRaises(ValueError):
            LegalizationService.sign_document(document)

    @patch("apps.legalization.services.sign_bytes")
    def test_cancel_document(self, mock_sign):
        """Test canceling a document."""
        mock_sign.return_value = MagicMock(
            pre_sign_hash="abc123",
            post_sign_hash="def456",
        )

        process = LegalizationProcess.objects.create(
            beneficiary=self.user,
            convocatoria=self.convocatoria,
        )
        document = LegalDocument.objects.create(
            process=process,
            document_type=LegalDocument.DocumentType.PAGARE,
        )

        result = LegalizationService.cancel_document(document)

        self.assertEqual(result.status, LegalDocument.Status.CANCELADO)
        self.assertEqual(process.status, LegalizationProcess.Status.CANCELADO)

    def test_cancel_legalized_document_raises(self):
        """Test that canceling a legalized document raises error."""
        process = LegalizationProcess.objects.create(
            beneficiary=self.user,
            convocatoria=self.convocatoria,
            status=LegalizationProcess.Status.LEGALIZADO,
        )
        document = LegalDocument.objects.create(
            process=process,
            document_type=LegalDocument.DocumentType.PAGARE,
            status=LegalDocument.Status.LEGALIZADO,
        )

        with self.assertRaises(ValueError):
            LegalizationService.cancel_document(document)
