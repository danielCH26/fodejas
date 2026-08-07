"""Views for termination and sanction management."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.condonation.models import Sanction, TerminationRequest
from apps.condonation.services import SanctionService, TerminationService


class TerminationRequestViewSet(viewsets.ModelViewSet):
    """ViewSet for termination requests."""

    queryset = TerminationRequest.objects.all()
    serializer_class = None  # TODO: Add serializers

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
    serializer_class = None  # TODO: Add serializers

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

    @action(detail=True, methods=["post"])
    def submit_justification(self, request, pk=None):
        """Submit justification for exception."""
        justification = request.data.get("justification")
        details = request.data.get("details", "")

        if not justification:
            return Response(
                {"error": "justification is required"},
                status=status.HTTP_400_BAD_REQUEST,
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
