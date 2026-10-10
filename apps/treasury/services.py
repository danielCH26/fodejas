"""Treasury service for disbursement management (CHG-802 hardened; CHG-303 gaps).

All mutating methods are wrapped in ``@transaction.atomic`` and
retrieve the row via ``select_for_update()`` so two concurrent
``authorize(...)`` / ``confirm_payment(...)`` calls serialize and
cannot both transition the same row (AUD-004).

CHG-303 gap fills:
  a) Doble firma: distinct users enforced; no self-signing.
  b) Adjuntos normativos: ``send_to_treasury()`` validates all 4
     LegalDocuments (PAGARE, CARTA_INSTRUCCIONES, CONTRATO,
     ACTO_ADMINISTRATIVO) are in LEGALIZADO status before the
     transition and records their UUIDs + post-sign hashes.
  c) Guard 5.1: ``create_authorization`` already requires LEGALIZADO.
  d) Audit 5.2: every service operation emits an audit event.
"""

from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_audit_event
from apps.legalization.models import LegalDocument
from apps.treasury.models import DisbursementAuthorization


# In-memory state holder shared by all method invocations. Holds
# audit log queries between tasks to keep sweep operations
# idempotent within a single worker process. Per CHG-802 the
# primary idempotency guard for the periodic tasks is the
# `last_alerted_at` column on the model, NOT this cache.
class TreasuryService:
    """Service for managing disbursement workflow (CAP-010)."""

    # The four normative attachment types that MUST be attached
    # to every treasury order (CHG-303 / design.md D1).
    REQUIRED_ATTACHMENT_TYPES = frozenset(
        [
            LegalDocument.DocumentType.PAGARE,
            LegalDocument.DocumentType.CARTA_INSTRUCCIONES,
            LegalDocument.DocumentType.CONTRATO,
            LegalDocument.DocumentType.ACTO_ADMINISTRATIVO,
        ]
    )

    @staticmethod
    @transaction.atomic
    def create_authorization(legalization_process, amount):
        """Create a disbursement authorization for a legalized process.

        Guard 5.1: refuses if the LegalizationProcess is not LEGALIZADO.

        CHG-303: emits AUDIT_DISBURSEMENT_CREATE.

        Args:
            legalization_process: LegalizationProcess instance
            amount: Decimal amount to disburse

        Returns:
            DisbursementAuthorization instance
        """
        if legalization_process.status != "LEGALIZADO":
            raise ValueError("Cannot create disbursement for non-legalized process")

        from decimal import Decimal

        if amount is None or Decimal(str(amount)) <= 0:
            raise ValueError("Amount must be a positive number.")

        authorization = DisbursementAuthorization.objects.create(
            legalization_process=legalization_process,
            amount=amount,
            status=DisbursementAuthorization.Status.PENDIENTE,
        )

        try:
            log_audit_event(
                actor=None,
                action="AUDIT_DISBURSEMENT_CREATE",
                entity="DisbursementAuthorization",
                entity_id=authorization.id,
                changes={
                    "amount": str(amount),
                    "legalization_process_id": str(legalization_process.id),
                    "status": authorization.status,
                },
                module="treasury",
            )
        except Exception:  # noqa: BLE001
            pass  # Do not fail the transaction on audit failure.

        return authorization

    @staticmethod
    @transaction.atomic
    def authorize(auth_id, user, role):
        """Authorize disbursement by one of the required signers.

        CHG-802: the row is fetched with ``select_for_update()`` so
        concurrent signers serialize. The first to acquire the lock
        wins; the second receives a clean ``ValueError`` (no double
        authorization, no silent overwrite).

        CHG-303 — doble firma:
          - Enforces two distinct roles (president, secretary).
          - Rejects self-signing: the same user cannot sign both roles.
          - Emits AUDIT_DISBURSEMENT_AUTHORIZE per signature.

        Args:
            auth_id: DisbursementAuthorization ID
            user: User instance
            role: 'president' or 'secretary'

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status != DisbursementAuthorization.Status.PENDIENTE:
            raise ValueError(f"Cannot authorize in {auth.status} status")

        if role == "president":
            # CHG-303: prevent self-signing.
            if (
                auth.authorized_by_secretary_id is not None
                and auth.authorized_by_secretary_id == user.id
            ):
                raise ValueError(
                    "Secretary has already signed; president cannot be "
                    "the same user as secretary."
                )
            if auth.authorized_by_president:
                raise ValueError("Already authorized by president")
            auth.authorized_by_president = user
        elif role == "secretary":
            # CHG-303: prevent self-signing.
            if (
                auth.authorized_by_president_id is not None
                and auth.authorized_by_president_id == user.id
            ):
                raise ValueError(
                    "President has already signed; secretary cannot be "
                    "the same user as president."
                )
            if auth.authorized_by_secretary:
                raise ValueError("Already authorized by secretary")
            auth.authorized_by_secretary = user
        else:
            raise ValueError("Invalid role. Use 'president' or 'secretary'")

        # Check if fully authorized
        if auth.is_fully_authorized:
            auth.status = DisbursementAuthorization.Status.AUTORIZADO
            auth.authorized_at = timezone.now()

        auth.save()

        # Audit per signature (CHG-303 / design.md §Audit 5.2).
        try:
            log_audit_event(
                actor=user,
                action="AUDIT_DISBURSEMENT_AUTHORIZE",
                entity="DisbursementAuthorization",
                entity_id=auth.id,
                changes={
                    "role": role,
                    "status_after": auth.status,
                    "is_fully_authorized": auth.is_fully_authorized,
                },
                module="treasury",
            )
        except Exception:  # noqa: BLE001
            pass  # Do not fail the transaction on audit failure.

        return auth

    @staticmethod
    @transaction.atomic
    def send_to_treasury(auth_id, order_number, actor=None):
        """Send authorized disbursement to Treasury.

        CHG-303 — adjuntos normativos (design.md D1):
          - Validates all 4 required LegalDocuments
            (PAGARE, CARTA_INSTRUCCIONES, CONTRATO, ACTO_ADMINISTRATIVO)
            are in LEGALIZADO status.
          - Records their UUIDs and post-sign hashes in
            ``treasury_order_attachments`` as evidence.

        Args:
            auth_id: DisbursementAuthorization ID
            order_number: Treasury order number
            actor: optional CustomUser triggering the dispatch (for audit).

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status != DisbursementAuthorization.Status.AUTORIZADO:
            raise ValueError("Must be authorized before sending to treasury")

        process = auth.legalization_process

        # CHG-303: validate all 4 normative attachments.
        all_docs = {doc.document_type: doc for doc in process.documents.all()}
        missing_types = [
            dt for dt in TreasuryService.REQUIRED_ATTACHMENT_TYPES if dt not in all_docs
        ]
        if missing_types:
            raise ValueError(
                f"Cannot send to treasury: missing legal documents "
                f"for types: {missing_types}. "
                f"Ensure all 4 documents (PAGARE, CARTA_INSTRUCCIONES, "
                f"CONTRATO, ACTO_ADMINISTRATIVO) exist in this process."
            )

        not_legalizado = [
            dt for dt, doc in all_docs.items() if doc.status != LegalDocument.Status.LEGALIZADO
        ]
        if not_legalizado:
            raise ValueError(
                f"Cannot send to treasury: the following documents are "
                f"not LEGALIZADO: {not_legalizado}. "
                f"All 4 normative documents must be finalized."
            )

        # Build attachment manifest with integrity evidence.
        attachments = [
            {
                "document_type": doc.document_type,
                "document_id": str(doc.id),
                "post_sign_hash": doc.post_sign_hash,
            }
            for doc in all_docs.values()
        ]

        auth.treasury_order_number = order_number
        auth.treasury_order_date = timezone.now().date()
        auth.treasury_order_attachments = attachments
        auth.status = DisbursementAuthorization.Status.ORDENADO
        auth.save()

        try:
            log_audit_event(
                actor=actor,
                action="AUDIT_DISBURSEMENT_SENT_TO_TREASURY",
                entity="DisbursementAuthorization",
                entity_id=auth.id,
                changes={
                    "order_number": order_number,
                    "attachments": [a["document_type"] for a in attachments],
                    "attachment_count": len(attachments),
                },
                module="treasury",
            )
        except Exception:  # noqa: BLE001
            pass

        return auth

    @staticmethod
    @transaction.atomic
    def mark_as_received(auth_id, treasury_user_id=None):
        """Mark an ordered authorization as received by Tesorería.

        CHG-303: emits AUDIT_DISBURSEMENT_RECEIVED.

        Args:
            auth_id: DisbursementAuthorization ID
            treasury_user_id: optional user FK for audit trail
                (not stored on the row directly; the audit event
                writes the actor).

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status != DisbursementAuthorization.Status.ORDENADO:
            raise ValueError(f"Cannot mark as received in {auth.status} status")

        auth.treasury_received_at = timezone.now()
        auth.status = DisbursementAuthorization.Status.RECIBIDO
        auth.save()

        try:
            log_audit_event(
                actor=None,
                action="AUDIT_DISBURSEMENT_RECEIVED",
                entity="DisbursementAuthorization",
                entity_id=auth.id,
                changes={
                    "previous_status": DisbursementAuthorization.Status.ORDENADO,
                    "treasury_order_number": auth.treasury_order_number,
                },
                module="treasury",
            )
        except Exception:  # noqa: BLE001
            pass

        return auth

    @staticmethod
    @transaction.atomic
    def confirm_payment(auth_id, payment_proof=None, actor=None):
        """Confirm payment from Treasury.

        CHG-802: the order MUST be in ``RECIBIDO`` state before
        we transition to ``PAGADO``. ``mark_as_received(...)`` is
        the entry point that Tesorería triggers once it has the
        order in its queue.

        CHG-303 / design.md D2: ``payment_proof`` (comprobante) is
        accepted but not forced here — the reconciliation VIEW enforces
        that the comprobante is attached before confirming payment.

        CHG-303: emits AUDIT_DISBURSEMENT_PAID.

        Args:
            auth_id: DisbursementAuthorization ID
            payment_proof: File upload with proof of payment
            actor: optional CustomUser confirming (for audit).

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status != DisbursementAuthorization.Status.RECIBIDO:
            raise ValueError(
                "Order must be RECIBIDO before confirming payment "
                f"(current status: {auth.status})"
            )

        auth.status = DisbursementAuthorization.Status.PAGADO
        auth.paid_at = timezone.now()
        if payment_proof:
            auth.payment_proof = payment_proof
        auth.save()

        try:
            log_audit_event(
                actor=actor,
                action="AUDIT_DISBURSEMENT_PAID",
                entity="DisbursementAuthorization",
                entity_id=auth.id,
                changes={
                    "amount": str(auth.amount),
                    "has_payment_proof": auth.payment_proof is not None,
                    "treasury_order_number": auth.treasury_order_number,
                },
                module="treasury",
            )
        except Exception:  # noqa: BLE001:
            pass

        return auth

    @staticmethod
    @transaction.atomic
    def reject(auth_id, reason, actor=None):
        """Reject disbursement authorization.

        CHG-303: emits AUDIT_DISBURSEMENT_REJECT.

        Args:
            auth_id: DisbursementAuthorization ID
            reason: Rejection reason
            actor: optional CustomUser rejecting (for audit).

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status in [
            DisbursementAuthorization.Status.PAGADO,
            DisbursementAuthorization.Status.RECHAZADO,
            DisbursementAuthorization.Status.VENCIDO,
        ]:
            raise ValueError(f"Cannot reject in {auth.status} status")

        previous_status = auth.status
        auth.status = DisbursementAuthorization.Status.RECHAZADO
        auth.notes = f"Rechazado: {reason}"
        auth.save()

        try:
            log_audit_event(
                actor=actor,
                action="AUDIT_DISBURSEMENT_REJECT",
                entity="DisbursementAuthorization",
                entity_id=auth.id,
                changes={
                    "reason": reason,
                    "previous_status": previous_status,
                    "amount": str(auth.amount),
                },
                module="treasury",
            )
        except Exception:  # noqa: BLE001:
            pass

        return auth
