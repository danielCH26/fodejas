"""Serializers for audit app."""
from rest_framework import serializers

from .models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    """Serializer for AuditEvent model."""

    actor_email = serializers.EmailField(source="actor.email", read_only=True)

    class Meta:
        model = AuditEvent
        fields = [
            "id",
            "timestamp",
            "actor",
            "actor_email",
            "action",
            "entity",
            "entity_id",
            "changes",
            "ip_address",
            "user_agent",
            "module",
            "previous_hash",
            "current_hash",
            "is_valid",
        ]
        read_only_fields = fields


class AuditChainVerifySerializer(serializers.Serializer):
    """Serializer for chain verification result."""

    is_valid = serializers.BooleanField()
    last_valid_hash = serializers.CharField()
    break_point = serializers.UUIDField(allow_null=True)
