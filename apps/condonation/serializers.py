"""DRF serializers for termination and sanction management (CHG-304)."""

from rest_framework import serializers

from apps.condonation.models import Sanction, TerminationRequest


class TerminationRequestSerializer(serializers.ModelSerializer):
    """Read representation of a termination request.

    Mutations flow through the ViewSet custom actions, which call
    ``TerminationService`` directly — the serializer is read-only by
    design (design.md: transitions validated in the service layer).
    """

    legalization_process = serializers.PrimaryKeyRelatedField(read_only=True)
    requested_by = serializers.StringRelatedField(read_only=True)
    reviewed_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = TerminationRequest
        fields = [
            "id",
            "legalization_process",
            "cause",
            "status",
            "description",
            "requested_by",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SanctionSerializer(serializers.ModelSerializer):
    """Read representation of a sanction with its termination link."""

    termination = serializers.PrimaryKeyRelatedField(read_only=True)
    reviewed_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Sanction
        fields = [
            "id",
            "termination",
            "base_amount",
            "ipc_adjustment",
            "total_amount",
            "status",
            "justification",
            "justification_details",
            "justification_approved",
            "fecha_limite",
            "paid_at",
            "reviewed_by",
            "reviewed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
