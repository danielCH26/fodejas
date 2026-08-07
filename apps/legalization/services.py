"""Legalization service for managing legal documents."""

from datetime import UTC, datetime

from apps.legalization.models import LegalDocument, LegalizationProcess
from apps.legalization.signer import sign_document as sign_bytes


class LegalizationService:
    """Service for managing legal document workflow."""

    @staticmethod
    def create_process_for_beneficiary(beneficiary, convocatoria):
        """Create a legalization process for a beneficiary.

        Args:
            beneficiary: User instance
            convocatoria: Convocatory instance

        Returns:
            LegalizationProcess instance
        """
        process, _ = LegalizationProcess.objects.get_or_create(
            beneficiary=beneficiary,
            convocatoria=convocatoria,
            defaults={"status": LegalizationProcess.Status.PENDIENTE},
        )

        # Create required documents if they don't exist
        for doc_type in LegalDocument.DocumentType.choices:
            LegalDocument.objects.get_or_create(
                process=process,
                document_type=doc_type[0],
                defaults={"status": LegalDocument.Status.PENDIENTE},
            )

        return process

    @staticmethod
    def sign_document(document, actor_id=None):
        """Sign a legal document.

        Args:
            document: LegalDocument instance
            actor_id: ID of user performing the signing

        Returns:
            Updated LegalDocument instance
        """
        if document.status != LegalDocument.Status.PENDIENTE:
            raise ValueError(f"Cannot sign document in {document.status} status")

        # Generate PDF content (placeholder - would use WeasyPrint in production)
        pdf_content = f"Legal Document: {document.document_type}".encode()

        # Sign using the electronic signature service
        result = sign_bytes(
            pdf_content,
            document_type=f"legal_{document.document_type.lower()}",
            actor_id=actor_id,
        )

        # Update document with signature hashes
        document.pre_sign_hash = result.pre_sign_hash
        document.post_sign_hash = result.post_sign_hash
        document.status = LegalDocument.Status.FIRMADO
        document.signed_at = datetime.now(UTC)
        document.save()

        # Check if all documents are signed
        LegalizationService._check_process_completion(document.process)

        return document

    @staticmethod
    def _check_process_completion(process):
        """Check if all documents in a process are signed.

        Args:
            process: LegalizationProcess instance
        """
        unsigned = process.documents.filter(status=LegalDocument.Status.PENDIENTE).exists()

        if not unsigned:
            # All documents signed - mark process as complete
            process.status = LegalizationProcess.Status.LEGALIZADO
            process.completed_at = datetime.now(UTC)
            process.save()

    @staticmethod
    def cancel_document(document):
        """Cancel a legal document.

        Args:
            document: LegalDocument instance

        Returns:
            Updated LegalDocument instance
        """
        if document.status == LegalDocument.Status.LEGALIZADO:
            raise ValueError("Cannot cancel a legalized document")

        document.status = LegalDocument.Status.CANCELADO
        document.save()

        # Also cancel the process
        document.process.status = LegalizationProcess.Status.CANCELADO
        document.process.save()

        return document
