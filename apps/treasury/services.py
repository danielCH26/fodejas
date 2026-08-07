"""Treasury service for disbursement management."""

from datetime import UTC, datetime

from apps.treasury.models import DisbursementAuthorization


class TreasuryService:
    """Service for managing disbursement workflow."""

    @staticmethod
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
    def authorize(auth_id, user, role):
        """Authorize disbursement by one of the required signers.

        Args:
            auth_id: DisbursementAuthorization ID
            user: User instance
            role: 'president' or 'secretary'

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = DisbursementAuthorization.objects.get(id=auth_id)
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
            auth.authorized_at = datetime.now(UTC)

        auth.save()
        return auth

    @staticmethod
    def send_to_treasury(auth_id, order_number):
        """Send authorized disbursement to Treasury.

        Args:
            auth_id: DisbursementAuthorization ID
            order_number: Treasury order number

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = DisbursementAuthorization.objects.get(id=auth_id)
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status != DisbursementAuthorization.Status.AUTORIZADO:
            raise ValueError("Must be authorized before sending to treasury")

        auth.treasury_order_number = order_number
        auth.treasury_order_date = datetime.now(UTC).date()
        auth.status = DisbursementAuthorization.Status.ORDENADO
        auth.save()

        return auth

    @staticmethod
    def confirm_payment(auth_id, payment_proof=None):
        """Confirm payment from Treasury.

        Args:
            auth_id: DisbursementAuthorization ID
            payment_proof: File upload with proof of payment

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = DisbursementAuthorization.objects.get(id=auth_id)
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status != DisbursementAuthorization.Status.ORDENADO:
            raise ValueError("Must be ordered to treasury before confirming payment")

        auth.status = DisbursementAuthorization.Status.PAGADO
        auth.paid_at = datetime.now(UTC)
        if payment_proof:
            auth.payment_proof = payment_proof
        auth.save()

        return auth

    @staticmethod
    def reject(auth_id, reason):
        """Reject disbursement authorization.

        Args:
            auth_id: DisbursementAuthorization ID
            reason: Rejection reason

        Returns:
            Updated DisbursementAuthorization instance
        """
        try:
            auth = DisbursementAuthorization.objects.get(id=auth_id)
        except DisbursementAuthorization.DoesNotExist:
            raise ValueError("Authorization not found") from None

        if auth.status in [
            DisbursementAuthorization.Status.PAGADO,
            DisbursementAuthorization.Status.RECHAZADO,
        ]:
            raise ValueError(f"Cannot reject in {auth.status} status")

        auth.status = DisbursementAuthorization.Status.RECHAZADO
        auth.notes = f"Rechazado: {reason}"
        auth.save()

        return auth
