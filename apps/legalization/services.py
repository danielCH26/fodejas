"""Legalization service for managing legal documents."""
from __future__ import annotations

from datetime import UTC, datetime

from django.utils import timezone

from apps.audit.services import log_audit_event
from apps.legalization.models import LegalDocument, LegalizationProcess
from apps.legalization.signer import (
    SignatureResult,
    SignerFactory,
    sign_document as sign_bytes,
)


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
            pass  # noqa: E501  # process complete logic goes here in CHG-302


def sign_legal_document(
    document: LegalDocument,
    actor=None,
) -> SignatureResult:
    """Sign a ``LegalDocument`` using the configured signer (CHG-301).

    Reads ``document.pdf``, computes the hash chain via the configured
    signer (``SIGNATURE_PROVIDER`` setting → ``SignerFactory``), and
    persists ``pre_sign_hash``, ``post_sign_hash``, ``signed_at`` and
    metadata in ``document.changes``. Registers an audit event via
    CHG-801.

    Idempotent: a second call on the same document with the same PDF
    is a no-op (no second audit event, no change to ``post_sign_hash``
    or ``signed_at``).

    Args:
        document: ``LegalDocument`` instance with a non-empty ``pdf``
            FileField.
        actor: optional ``CustomUser`` performing the signing.

    Returns:
        ``SignatureResult`` from the signer.

    Raises:
        ValueError: if ``document.pdf`` is empty.
    """
    import hashlib

    if not document.pdf:
        raise ValueError(
            f"LegalDocument {document.uuid} no tiene PDF cargado; "
            f"cargue el pagaré / carta / contrato antes de firmar."
        )

    document.pdf.seek(0)
    pdf_bytes = document.pdf.read()
    pre_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # Idempotency check: if the document was already signed with this
    # exact PDF, return the cached SignatureResult without re-firing.
    if document.post_sign_hash and document.pre_sign_hash == pre_hash:
        # Build a synthetic SignatureResult from the persisted metadata
        # without re-running the signer (avoids creating a duplicate
        # audit event and avoids double timestamps).
        return SignatureResult(
            pre_sign_hash=document.pre_sign_hash,
            post_sign_hash=document.post_sign_hash,
            metadata=document.changes or {},
            provider=(document.changes or {}).get("provider", "unknown"),
        )

    signer = SignerFactory.get_provider()
    result = signer.sign(pdf_bytes)

    document.pre_sign_hash = result.pre_sign_hash
    document.post_sign_hash = result.post_sign_hash
    document.signed_at = timezone.now()
    document.changes = result.metadata
    document.save()

    # Audit event via CHG-801.
    try:
        log_audit_event(
            actor=actor,
            action="ELECTRONIC_SIGNATURE",
            entity=f"legal_{document.document_type.lower()}",
            entity_id=document.uuid,
            changes={
                "pre_sign_hash": result.pre_sign_hash,
                "post_sign_hash": result.post_sign_hash,
                "provider": result.provider,
                "metadata": result.metadata,
                "legal_document_uuid": str(document.uuid),
            },
            module="legalization",
        )
    except Exception:
        # Audit failures must NOT abort signing — the signer contract
        # is independent of the audit log. But the failure is logged
        # loudly so operators see it.
        import logging
        logging.getLogger(__name__).exception(
            "audit: signature audit log failed (CHG-301) for %s", document.uuid
        )

    return result
