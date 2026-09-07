"""Treasury service for disbursement management (CHG-802 hardened).

All mutating methods are wrapped in ``@transaction.atomic`` and
retrieve the row via ``select_for_update()`` so two concurrent
``authorize(...)`` / ``confirm_payment(...)`` calls serialize and
cannot both transition the same row (AUD-004).
"""
from datetime import UTC, datetime

from django.db import transaction
from django.utils import timezone

from apps.treasury.models import DisbursementAuthorization


# In-memory state holder shared by all method invocations. Holds
# audit log queries between tasks to keep sweep operations
# idempotent within a single worker process. Per CHG-802 the
# primary idempotency guard for the periodic tasks is the
# `last_alerted_at` column on the model, NOT this cache.
class TreasuryService:
    """Service for managing disbursement workflow."""

    @staticmethod
    @transaction.atomic
    def create_authorization(legalization_process, amount):
        """Create a disbursement authorization for a legalized process.

        Args:
            legalization_process: LegalizationProcess instance
            amount: Decimal amount to disburse

        Returns:
            DisbursementAuthorization instance
        """
        # Verify legalization is complete
        if legalization_process.status != "LEGALIZADO":
            raise ValueError("Cannot create disbursement for non-legalized process")

        authorization = DisbursementAuthorization.objects.create(
            legalization_process=legalization_process,
            amount=amount,
            status=DisbursementAuthorization.Status.PENDIENTE,
        )

        return authorization

    @staticmethod
    @transaction.atomic
    def authorize(auth_id, user, role):
        """Authorize disbursement by one of the required signers.

        CHG-802: the row is fetched with ``select_for_update()`` so
        concurrent signers serialize. The first to acquire the lock
        wins; the second receives a clean ``ValueError`` (no double
        authorization, no silent overwrite).

        Args:
            auth_id: DisbursementAuthorization ID
            user: User instance
            role: 'president' or 'secretary'

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = (
                DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
            )
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status != DisbursementAuthorization.Status.PENDIENTE:
            raise ValueError(f"Cannot authorize in {auth.status} status")

        if role == "president":
            if auth.authorized_by_president:
                raise ValueError("Already authorized by president")
            auth.authorized_by_president = user
        elif role == "secretary":
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
        return auth

    @staticmethod
    @transaction.atomic
    def send_to_treasury(auth_id, order_number):
        """Send authorized disbursement to Treasury.

        Args:
            auth_id: DisbursementAuthorization ID
            order_number: Treasury order number

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = (
                DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
            )
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status != DisbursementAuthorization.Status.AUTORIZADO:
            raise ValueError("Must be authorized before sending to treasury")

        auth.treasury_order_number = order_number
        auth.treasury_order_date = timezone.now().date()
        auth.status = DisbursementAuthorization.Status.ORDENADO
        auth.save()

        return auth

    @staticmethod
    @transaction.atomic
    def mark_as_received(auth_id, treasury_user_id=None):
        """Mark an ordered authorization as received by Tesorería.

        Args:
            auth_id: DisbursementAuthorization ID
            treasury_user_id: optional user FK for audit trail
                (not stored on the row directly; the audit event
                writes the actor).

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = (
                DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
            )
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status != DisbursementAuthorization.Status.ORDENADO:
            raise ValueError(
                f"Cannot mark as received in {auth.status} status"
            )

        auth.treasury_received_at = timezone.now()
        auth.status = DisbursementAuthorization.Status.RECIBIDO
        auth.save()
        return auth

    @staticmethod
    @transaction.atomic
    def confirm_payment(auth_id, payment_proof=None):
        """Confirm payment from Treasury.

        CHG-802: the order MUST be in ``RECIBIDO`` state before
        we transition to ``PAGADO``. ``mark_as_received(...)`` is
        the entry point that Tesorería triggers once it has the
        order in its queue.

        Args:
            auth_id: DisbursementAuthorization ID
            payment_proof: File upload with proof of payment

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = (
                DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
            )
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

        return auth

    @staticmethod
    @transaction.atomic
    def reject(auth_id, reason):
        """Reject disbursement authorization.

        Args:
            auth_id: DisbursementAuthorization ID
            reason: Rejection reason

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = (
                DisbursementAuthorization.objects.select_for_update().get(id=auth_id)
            )
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status in [
            DisbursementAuthorization.Status.PAGADO,
            DisbursementAuthorization.Status.RECHAZADO,
            DisbursementAuthorization.Status.VENCIDO,
        ]:
            raise ValueError(f"Cannot reject in {auth.status} status")

        auth.status = DisbursementAuthorization.Status.RECHAZADO
        auth.notes = f"Rechazado: {reason}"
        auth.save()

        return auth
