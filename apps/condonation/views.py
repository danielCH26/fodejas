"""Views for termination and sanction management."""

from django.utils.translation import gettext as _

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole
from apps.condonation.models import Sanction, TerminationRequest
from apps.condonation.serializers import (
    SanctionSerializer,
    TerminationRequestSerializer,
)
from apps.condonation.services import SanctionService, TerminationService

# CAP-015/016 fine-grained role matrix:
# - TerminationRequestViewSet: R-JUNTA (aprueba), R-ADMIN, R-COORD (gestiona)
# - SanctionViewSet: same; submit_justification is beneficiary-facing
#   with ownership check (beneficiary = termination.legalization_process.beneficiary)
# Superusers bypass.


class _CondonationManagementPermission(HasAnyRole):
    """Permission for termination/sanction management (R-JUNTA, R-ADMIN, R-COORD)."""

    def __init__(self):
        # DRF calls permission classes as constructors, so __init__ takes no args
        super().__init__(role_codes=["R-JUNTA", "R-ADMIN", "R-COORD"])

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.user_roles.filter(role__code__in=self.role_codes).exists()


def _can_submit_justification(user, sanction: Sanction) -> bool:
    """
    Return True if ``user`` may submit a justification for ``sanction``.

    Allowed when:
      - user is the beneficiary of the sanction's termination process, OR
      - user has R-JUNTA / R-ADMIN (staff-of-flow)
    """
    if user.is_superuser:
        return True
    # Staff-of-flow bypass
    if user.user_roles.filter(role__code__in=["R-JUNTA", "R-ADMIN"]).exists():
        return True
    # Ownership check: user must be the beneficiary of the linked process
    try:
        return sanction.termination.legalization_process.beneficiary_id == user.id
    except Exception:  # pragma: no cover — defensive
        return False


class TerminationRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for termination requests."""

    queryset = TerminationRequest.objects.all()
    serializer_class = TerminationRequestSerializer
    permission_classes = [_CondonationManagementPermission]

    def create(self, request, *args, **kwargs):
        """Create a new termination request."""
        legalization_id = request.data.get("legalization_process")
        cause = request.data.get("cause")
        description = request.data.get("description", "")

        if not legalization_id or not cause:
            return Response(
                {"error": "legalization_process and cause are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            from apps.legalization.models import LegalizationProcess

            process = LegalizationProcess.objects.get(id=legalization_id)
            termination = TerminationService.create_termination(
                process, cause, request.user, description
            )
            return Response(
                {"id": str(termination.id), "status": termination.status},
                status=status.HTTP_201_CREATED,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a termination request."""
        try:
            termination = TerminationService.approve_termination(pk, request.user)
            return Response({"status": termination.status})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a termination request."""
        try:
            termination = TerminationService.reject_termination(pk, request.user)
            return Response({"status": termination.status})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def handle_death(self, request, pk=None):
        """Handle termination due to death."""
        try:
            termination = TerminationService.handle_death_termination(pk, request.user)
            return Response({"status": termination.status})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SanctionViewSet(viewsets.ModelViewSet):
    """ViewSet for sanctions."""

    queryset = Sanction.objects.all()
    serializer_class = SanctionSerializer
    permission_classes = [_CondonationManagementPermission]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Approve a sanction."""
        try:
            sanction = SanctionService.approve_sanction(pk, request.user)
            return Response({"status": sanction.status})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject a sanction."""
        try:
            sanction = SanctionService.reject_sanction(pk, request.user)
            return Response({"status": sanction.status})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def submit_justification(self, request, pk=None):
        """
        Submit justification for exception.

        Access:
          - IsAuthenticated (beneficiary of the sanction's process, OR R-JUNTA/R-ADMIN)
          - Ownership check: user must be the beneficiary of the linked
            termination.legalization_process, or have R-JUNTA/R-ADMIN.
        """
        justification = request.data.get("justification")
        details = request.data.get("details", "")

        if not justification:
            return Response(
                {"error": "justification is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sanction = Sanction.objects.select_related("termination__legalization_process").get(
                pk=pk
            )
        except Sanction.DoesNotExist:
            return Response({"error": "Sanction not found"}, status=status.HTTP_404_NOT_FOUND)

        if not _can_submit_justification(request.user, sanction):
            return Response(
                {"error": _("No tienes permiso para enviar justificación para esta sanción")},
                status=status.HTTP_403_FORBIDDEN,
            )

        try:
            sanction = SanctionService.submit_justification(pk, justification, details)
            return Response({"status": sanction.status})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def approve_justification(self, request, pk=None):
        """Approve justification and condone sanction."""
        try:
            sanction = SanctionService.approve_justification(pk, request.user)
            return Response({"status": sanction.status})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def confirm_payment(self, request, pk=None):
        """Confirm payment of sanction."""
        payment_proof = request.FILES.get("payment_proof")

        if not payment_proof:
            return Response(
                {"error": "payment_proof is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            sanction = SanctionService.confirm_payment(pk, payment_proof, request.user)
            return Response({"status": sanction.status})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
