"""Services for termination and sanction management."""

from datetime import UTC, datetime
from decimal import Decimal

from django.db import transaction

from apps.condonation.models import Sanction, TerminationRequest

# Valid causes that trigger automatic sanction per Art. 17
SANCTION_TRIGGER_CAUSES = [
    TerminationRequest.Cause.INFORMACION_FALSA,
    TerminationRequest.Cause.SANCION_DISCIPLINARIA,
]


def calculate_ipc_adjustment(
    base_amount: Decimal, years: int, annual_rate: Decimal = Decimal("0.05")
) -> Decimal:
    """Calculate IPC adjustment over time.

    Args:
        base_amount: Original amount
        years: Number of years since disbursement
        annual_rate: Annual IPC rate (default 5%)

    Returns:
        IPC adjustment amount
    """
    if years <= 0:
        return Decimal("0")
    # Simple compound: amount * (1 + rate)^years - amount
    adjustment = base_amount * ((1 + annual_rate) ** years - 1)
    return adjustment.quantize(Decimal("0.01"))


class TerminationService:
    """Service for managing termination requests."""

    @staticmethod
    def create_termination(legalization_process, cause, requested_by, description=""):
        """Create a new termination request.

        Args:
            legalization_process: LegalizationProcess instance
            cause: Termination cause from Cause choices
            requested_by: User requesting termination
            description: Optional description

        Returns:
            TerminationRequest instance
        """
        # Verify process is legalized
        if legalization_process.status != "LEGALIZADO":
            raise ValueError("Can only terminate legalized processes")

        termination = TerminationRequest.objects.create(
            legalization_process=legalization_process,
            cause=cause,
            status=TerminationRequest.Status.PENDIENTE,
            description=description,
            requested_by=requested_by,
        )

        return termination

    @staticmethod
    def approve_termination(termination_id, reviewed_by):
        """Approve a termination request.

        Args:
            termination_id: TerminationRequest ID
            reviewed_by: User approving

        Returns:
            Updated TerminationRequest instance
        """
        try:
            termination = TerminationRequest.objects.get(id=termination_id)
        except TerminationRequest.DoesNotExist:
            raise ValueError("Termination not found") from None

        if termination.status != TerminationRequest.Status.PENDIENTE:
            raise ValueError(f"Cannot approve in {termination.status} status")

        termination.status = TerminationRequest.Status.TERMINADO
        termination.reviewed_by = reviewed_by
        termination.reviewed_at = datetime.now(UTC)
        termination.save()

        # Auto-create sanction for fraud causes
        if termination.cause in SANCTION_TRIGGER_CAUSES:
            SanctionService.create_sanction_from_termination(termination)

        return termination

    @staticmethod
    def reject_termination(termination_id, reviewed_by):
        """Reject a termination request.

        Args:
            termination_id: TerminationRequest ID
            reviewed_by: User rejecting

        Returns:
            Updated TerminationRequest instance
        """
        try:
            termination = TerminationRequest.objects.get(id=termination_id)
        except TerminationRequest.DoesNotExist:
            raise ValueError("Termination not found") from None

        if termination.status != TerminationRequest.Status.PENDIENTE:
            raise ValueError(f"Cannot reject in {termination.status} status")

        termination.status = TerminationRequest.Status.RECHAZADO
        termination.reviewed_by = reviewed_by
        termination.reviewed_at = datetime.now(UTC)
        termination.save()

        return termination

    @staticmethod
    def handle_death_termination(termination_id, reviewed_by):
        """Handle termination due to death - auto-condones all sanctions.

        Args:
            termination_id: TerminationRequest ID
            reviewed_by: User processing

        Returns:
            Updated TerminationRequest instance
        """
        try:
            termination = TerminationRequest.objects.get(id=termination_id)
        except TerminationRequest.DoesNotExist:
            raise ValueError("Termination not found") from None

        if termination.cause != TerminationRequest.Cause.MUERTE:
            raise ValueError("This handler is only for death terminations")

        termination.status = TerminationRequest.Status.TERMINADO
        termination.reviewed_by = reviewed_by
        termination.reviewed_at = datetime.now(UTC)
        termination.save()

        # Condon all active sanctions
        if hasattr(termination, "sanction"):
            sanction = termination.sanction
            SanctionService.condone_sanction(sanction.id, reviewed_by)

        return termination


class SanctionService:
    """Service for managing sanctions and reintegration."""

    @staticmethod
    @transaction.atomic
    def create_sanction_from_termination(termination, base_amount=None):
        """Create sanction from termination (for fraud causes).

        Args:
            termination: TerminationRequest instance
            base_amount: Amount to reimburse (calculated if not provided)

        Returns:
            Sanction instance
        """
        if termination.cause not in SANCTION_TRIGGER_CAUSES:
            raise ValueError("Sanction only created for fraud/discipline causes")

        # Calculate base amount from disbursements if not provided
        if base_amount is None:
            # TODO: Calculate from actual disbursements
            base_amount = Decimal("0")

        # Calculate IPC (simplified - actual implementation would track years)
        ipc = calculate_ipc_adjustment(base_amount, years=1)

        sanction = Sanction.objects.create(
            termination=termination,
            base_amount=base_amount,
            ipc_adjustment=ipc,
            total_amount=base_amount + ipc,
            status=Sanction.Status.PENDIENTE,
        )

        return sanction

    @staticmethod
    def approve_sanction(sanction_id, reviewed_by):
        """Approve a sanction.

        Args:
            sanction_id: Sanction ID
            reviewed_by: User approving

        Returns:
            Updated Sanction instance
        """
        try:
            sanction = Sanction.objects.get(id=sanction_id)
        except Sanction.DoesNotExist:
            raise ValueError("Sanction not found") from None

        if sanction.status != Sanction.Status.PENDIENTE:
            raise ValueError(f"Cannot approve in {sanction.status} status")

        sanction.status = Sanction.Status.APROBADA
        sanction.reviewed_by = reviewed_by
        sanction.reviewed_at = datetime.now(UTC)
        sanction.save()

        return sanction

    @staticmethod
    def reject_sanction(sanction_id, reviewed_by):
        """Reject a sanction.

        Args:
            sanction_id: Sanction ID
            reviewed_by: User rejecting

        Returns:
            Updated Sanction instance
        """
        try:
            sanction = Sanction.objects.get(id=sanction_id)
        except Sanction.DoesNotExist:
            raise ValueError("Sanction not found") from None

        if sanction.status != Sanction.Status.PENDIENTE:
            raise ValueError(f"Cannot reject in {sanction.status} status")

        sanction.status = Sanction.Status.RECHAZADA
        sanction.reviewed_by = reviewed_by
        sanction.reviewed_at = datetime.now(UTC)
        sanction.save()

        return sanction

    @staticmethod
    def submit_justification(sanction_id, justification, details):
        """Submit justification for exception.

        Args:
            sanction_id: Sanction ID
            justification: Justification type
            details: Detailed explanation

        Returns:
            Updated Sanction instance
        """
        # Validate justification
        valid_justifications = [j.value for j in Sanction.Justification]
        if justification not in valid_justifications:
            raise ValueError(f"Invalid justification. Must be one of: {valid_justifications}")

        try:
            sanction = Sanction.objects.get(id=sanction_id)
        except Sanction.DoesNotExist:
            raise ValueError("Sanction not found") from None

        if sanction.status not in [Sanction.Status.APROBADA, Sanction.Status.PENDIENTE]:
            raise ValueError(f"Cannot submit justification in {sanction.status} status")

        sanction.justification = justification
        sanction.justification_details = details
        sanction.status = Sanction.Status.EN_REVISION
        sanction.save()

        return sanction

    @staticmethod
    def approve_justification(sanction_id, reviewed_by):
        """Approve justification and condone sanction.

        Args:
            sanction_id: Sanction ID
            reviewed_by: User approving

        Returns:
            Updated Sanction instance
        """
        try:
            sanction = Sanction.objects.get(id=sanction_id)
        except Sanction.DoesNotExist:
            raise ValueError("Sanction not found") from None

        if not sanction.justification:
            raise ValueError("No justification submitted")

        sanction.justification_approved = True
        sanction.status = Sanction.Status.CONDONADA
        sanction.reviewed_by = reviewed_by
        sanction.reviewed_at = datetime.now(UTC)
        sanction.save()

        return sanction

    @staticmethod
    def condone_sanction(sanction_id, reviewed_by):
        """Condone a sanction (e.g., due to death).

        Args:
            sanction_id: Sanction ID
            reviewed_by: User condoning

        Returns:
            Updated Sanction instance
        """
        try:
            sanction = Sanction.objects.get(id=sanction_id)
        except Sanction.DoesNotExist:
            raise ValueError("Sanction not found") from None

        sanction.justification_approved = True
        sanction.status = Sanction.Status.CONDONADA
        sanction.reviewed_by = reviewed_by
        sanction.reviewed_at = datetime.now(UTC)
        sanction.save()

        return sanction

    @staticmethod
    def confirm_payment(sanction_id, payment_proof, reviewed_by):
        """Confirm payment of sanction.

        Args:
            sanction_id: Sanction ID
            payment_proof: File upload with proof
            reviewed_by: User confirming

        Returns:
            Updated Sanction instance
        """
        try:
            sanction = Sanction.objects.get(id=sanction_id)
        except Sanction.DoesNotExist:
            raise ValueError("Sanction not found") from None

        if sanction.status != Sanction.Status.APROBADA:
            raise ValueError("Must be approved before payment")

        sanction.payment_proof = payment_proof
        sanction.status = Sanction.Status.PAGADA
        sanction.paid_at = datetime.now(UTC)
        sanction.reviewed_by = reviewed_by
        sanction.save()

        return sanction
