"""Legalization service for managing legal documents (CHG-302, CAP-009)."""
from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import render_to_string
from django.utils import timezone

from apps.audit.services import log_audit_event
from apps.legalization.domain.transitions import (
    is_document_terminal,
    is_process_terminal,
    is_valid_document_transition,
    is_valid_process_transition,
)
from apps.legalization.models import LegalDocument, LegalizationProcess
from apps.legalization.signer import (
    SignatureResult,
    SignerFactory,
    sign_document as sign_bytes,
)

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------
# PDF renderer seam (WeasyPrint optional — see generate_pdf docstring)
# -------------------------------------------------------------------
try:
    from weasyprint import HTML as _WeasyHTML  # noqa: N813
    _WASYPRINT_AVAILABLE = True
except Exception:  # noqa: BLE001
    _WASYPRINT_AVAILABLE = False
    _WeasyHTML = None


# -------------------------------------------------------------------
# LegalizationService
# -------------------------------------------------------------------

class LegalizationService:
    """Service for managing legal document workflow (CHG-302, CAP-009).

    Public workflow methods (design.md D1, D2, D3):
      create_documents_for_beneficiary()  — creates PAGARE + CARTA_INSTRUCCIONES
                                           + CONTRATO per process
      generate_pdf()                      — renders one document to PDF, stores
                                           it, records SHA-256
      complete_legalization()             — all three documents FIRMADO →
                                           LEGALIZADO; refuses otherwise
      cancel_document()                    — cancel a non-terminal document
    """

    @staticmethod
    def create_process_for_beneficiary(beneficiary, convocatoria):
        """Create a legalization process and its three required documents.

        Idempotent: returns the existing process if one already exists for
        this (beneficiary, convocatoria) pair.

        Args:
            beneficiary: CustomUser instance
            convocatoria: Convocatory instance

        Returns:
            LegalizationProcess instance
        """
        process, _ = LegalizationProcess.objects.get_or_create(
            beneficiary=beneficiary,
            convocatoria=convocatoria,
            defaults={"status": LegalizationProcess.Status.PENDIENTE},
        )
        for doc_type, _ in LegalDocument.DocumentType.choices:
            LegalDocument.objects.get_or_create(
                process=process,
                document_type=doc_type,
                defaults={"status": LegalDocument.Status.PENDIENTE},
            )
        return process

    @staticmethod
    def create_documents_for_beneficiary(beneficiary, convocatoria):
        """Create or return all three legal documents for a beneficiary.

        Wrapper around create_process_for_beneficiary that returns the
        three LegalDocument instances (PAGARE, CARTA_INSTRUCCIONES, CONTRATO).

        Args:
            beneficiary: CustomUser instance
            convocatoria: Convocatory instance

        Returns:
            dict mapping document_type → LegalDocument instance
        """
        process = LegalizationService.create_process_for_beneficiary(
            beneficiary, convocatoria
        )
        return {
            doc.document_type: doc
            for doc in process.documents.all()
        }

    @staticmethod
    def generate_pdf(document, context: dict, actor=None):
        """Render a legal-document template to PDF, store it, record SHA-256.

        Implements design.md D2:
          1. Render the HTML template for the document type with *context*.
          2. Convert to PDF using WeasyPrint (or the seam renderer).
          3. Store the PDF in ``document.pdf``.
          4. Compute ``pre_sign_hash`` = SHA-256 of the raw PDF bytes.
          5. Log a GENERATE_PDF audit event.

        The renderer seam allows tests to inject a fake that returns
        controlled bytes without requiring GTK/Pango.

        Args:
            document: LegalDocument instance.
            context: dict passed into the template renderer.
            actor: optional CustomUser performing the generation.

        Returns:
            LegalDocument instance with pdf and pre_sign_hash populated.

        Raises:
            RuntimeError: if WeasyPrint is not available and no renderer
                has been injected.
        """
        template_map = {
            LegalDocument.DocumentType.PAGARE:
                "legalization/pdf/pagare.html",
            LegalDocument.DocumentType.CARTA_INSTRUCCIONES:
                "legalization/pdf/carta_instrucciones.html",
            LegalDocument.DocumentType.CONTRATO:
                "legalization/pdf/contrato.html",
        }
        template_name = template_map.get(document.document_type)
        if not template_name:
            raise ValueError(
                f"Unknown document_type {document.document_type!r}; "
                f"cannot select a PDF template."
            )

        # 1. Render HTML.
        html_string = render_to_string(template_name, context)

        # 2. Convert to PDF via seam.
        if _WASYPRINT_AVAILABLE and _WeasyHTML is not None:
            pdf_bytes = _WeasyHTML(string=html_string).write_pdf()
        else:
            raise RuntimeError(
                "WeasyPrint is not available. "
                "Install system dependencies (GTK/Pango) or inject a test renderer "
                "via apps.legalization.services._WeasyHTML."
            )

        # 3. Store PDF.
        filename = f"{document.document_type.lower()}_{document.id}.pdf"
        document.pdf.save(filename, ContentFile(pdf_bytes), save=False)

        # 4. Record pre-sign SHA-256.
        document.pre_sign_hash = hashlib.sha256(pdf_bytes).hexdigest()
        document.save(update_fields=["pdf", "pre_sign_hash"])

        # 5. Audit event.
        try:
            log_audit_event(
                actor=actor,
                action="GENERATE_PDF",
                entity=f"legal_{document.document_type.lower()}",
                entity_id=str(document.id),
                changes={
                    "pre_sign_hash": document.pre_sign_hash,
                    "document_type": document.document_type,
                    "legal_document_uuid": str(document.id),
                },
                module="legalization",
            )
        except Exception:  # noqa: BLE001
            logger.exception("audit: generate_pdf audit log failed for %s", document.id)

        return document

    @staticmethod
    def complete_legalization(process, actor=None):
        """Advance all FIRMADO documents to LEGALIZADO.

        Implements design.md D3:
          - Every document in the process must be FIRMADO.
          - If any document is PENDIENTE or CANCELADO, raise ValueError.
          - Advance each document to LEGALIZADO and mark the process
            LEGALIZADO.
          - Log a LEGALIZATION_COMPLETE audit event per document.

        Idempotent: calling this on an already-LEGALIZADO process is a
        no-op (no duplicate audit events, no state change).

        Args:
            process: LegalizationProcess instance.
            actor: optional CustomUser performing the action.

        Returns:
            LegalizationProcess instance (saved, possibly updated).

        Raises:
            ValueError: if not all documents are FIRMADO.
        """
        if process.status == LegalizationProcess.Status.LEGALIZADO:
            return process  # Already done — idempotent.

        documents = list(process.documents.all())
        if not documents:
            raise ValueError(
                f"Process {process.id} has no documents; "
                f"cannot complete legalization."
            )

        not_firmado = [
            d for d in documents
            if d.status != LegalDocument.Status.FIRMADO
        ]
        if not_firmado:
            doc_statuses = {d.document_type: d.status for d in not_firmado}
            raise ValueError(
                f"Cannot complete legalization: the following documents are not "
                f"FIRMADO: {doc_statuses}"
            )

        now = timezone.now()
        for doc in documents:
            old_status = doc.status
            doc.status = LegalDocument.Status.LEGALIZADO
            doc.save(update_fields=["status"])
            _log_transition_audit(
                doc=doc,
                action="LEGALIZATION_COMPLETE",
                old_status=old_status,
                new_status=LegalDocument.Status.LEGALIZADO,
                actor=actor,
            )

        process.status = LegalizationProcess.Status.LEGALIZADO
        process.completed_at = now
        process.save(update_fields=["status", "completed_at"])
        return process

    @staticmethod
    def cancel_document(document, actor=None):
        """Cancel a non-terminal legal document.

        Guards against cancelling FIRMADO or LEGALIZADO documents.
        The transition PENDIENTE → CANCELADO and FIRMADO → CANCELADO are
        both allowed per design.md D3.

        Args:
            document: LegalDocument instance.
            actor: optional CustomUser performing the action.

        Returns:
            LegalDocument instance (saved, status=CANCELADO).

        Raises:
            ValueError: if the document is already in a terminal state.
        """
        if is_document_terminal(document.status):
            raise ValueError(
                f"Cannot cancel document {document.id} in terminal "
                f"status {document.status!r}."
            )
        if not is_valid_document_transition(
            document.status, LegalDocument.Status.CANCELADO
        ):
            raise ValueError(
                f"Invalid transition {document.status} → CANCELADO "
                f"for document {document.id}."
            )

        old_status = document.status
        document.status = LegalDocument.Status.CANCELADO
        document.save(update_fields=["status"])

        _log_transition_audit(
            doc=document,
            action="DOCUMENT_CANCELLED",
            old_status=old_status,
            new_status=LegalDocument.Status.CANCELADO,
            actor=actor,
        )
        return document


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------

def _log_transition_audit(doc, action, old_status, new_status, actor=None):
    """Log a document state transition to the audit trail."""
    try:
        log_audit_event(
            actor=actor,
            action=action,
            entity=f"legal_{doc.document_type.lower()}",
            entity_id=str(doc.id),
            changes={
                "old_status": old_status,
                "new_status": new_status,
                "legal_document_uuid": str(doc.id),
            },
            module="legalization",
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "audit: transition audit log failed for %s (%s → %s)",
            doc.id, old_status, new_status
        )


# -------------------------------------------------------------------
# Backwards-compatible module-level function (CHG-301)
# -------------------------------------------------------------------

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
    if not document.pdf:
        raise ValueError(
            f"LegalDocument {document.id} no tiene PDF cargado; "
            f"cargue el pagaré / carta / contrato antes de firmar."
        )

    document.pdf.seek(0)
    pdf_bytes = document.pdf.read()
    pre_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # Idempotency check: if the document was already signed with this
    # exact PDF, return the cached SignatureResult without re-firing.
    if document.post_sign_hash and document.pre_sign_hash == pre_hash:
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
    document.status = LegalDocument.Status.FIRMADO
    document.changes = result.metadata
    document.save()

    # Audit event via CHG-801.
    try:
        log_audit_event(
            actor=actor,
            action="ELECTRONIC_SIGNATURE",
            entity=f"legal_{document.document_type.lower()}",
            entity_id=str(document.id),
            changes={
                "pre_sign_hash": result.pre_sign_hash,
                "post_sign_hash": result.post_sign_hash,
                "provider": result.provider,
                "metadata": result.metadata,
                "legal_document_uuid": str(document.id),
            },
            module="legalization",
        )
    except Exception:  # noqa: BLE001
        logger.getLogger(__name__).exception(
            "audit: signature audit log failed (CHG-301) for %s", document.id
        )

    return result
