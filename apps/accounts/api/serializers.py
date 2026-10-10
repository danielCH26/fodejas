"""Serializers for accounts API."""
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from apps.accounts.models import Consentimiento, Notification, SolicitudHabeasData


class ConsentimientoSerializer(serializers.ModelSerializer):
    """Serializer for Consentimiento model."""

    titular_email = serializers.EmailField(source="titular.email", read_only=True)

    class Meta:
        model = Consentimiento
        fields = [
            "id",
            "titular",
            "titular_email",
            "tipo",
            "version_texto",
            "version_etiqueta",
            "hash_texto",
            "pdf_url",
            "ip",
            "user_agent",
            "otorgado_en",
            "revocado_en",
        ]
        read_only_fields = [
            "id",
            "titular_email",
            "hash_texto",
            "otorgado_en",
            "revocado_en",
        ]


class SolicitudHabeasDataSerializer(serializers.ModelSerializer):
    """Serializer for SolicitudHabeasData model."""

    titular_email = serializers.EmailField(source="titular.email", read_only=True)
    dias_restantes = serializers.SerializerMethodField()

    class Meta:
        model = SolicitudHabeasData
        fields = [
            "id",
            "titular",
            "titular_email",
            "tipo",
            "estado",
            "descripcion",
            "fecha_radicacion",
            "fecha_limite",
            "respuesta",
            "motivo_rechazo",
            "evidencia_url",
            "resuelto_por",
            "resuelto_en",
            "suprimido_en",
            "dias_restantes",
        ]
        read_only_fields = [
            "id",
            "titular_email",
            "estado",
            "fecha_radicacion",
            "fecha_limite",
            "respuesta",
            "motivo_rechazo",
            "evidencia_url",
            "resuelto_por",
            "resuelto_en",
            "suprimido_en",
            "dias_restantes",
        ]

    def get_dias_restantes(self, obj):
        """Calculate remaining days until deadline."""
        from django.utils import timezone
        if obj.fecha_limite:
            remaining = obj.fecha_limite - timezone.now()
            return max(0, remaining.days)
        return None


class SolicitudHabeasDataCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating SolicitudHabeasData."""

    class Meta:
        model = SolicitudHabeasData
        fields = [
            "tipo",
            "descripcion",
        ]

    def validate(self, attrs):
        """Validate the request."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # Check if user has an active request of the same type
            from datetime import timedelta

            from django.utils import timezone

            from apps.accounts.models import SolicitudHabeasData

            # Check for duplicate request in the last week
            one_week_ago = timezone.now() - timedelta(days=7)
            duplicate = SolicitudHabeasData.objects.filter(
                titular=request.user,
                tipo=attrs.get("tipo"),
                fecha_radicacion__gte=one_week_ago,
            ).exists()

            if duplicate:
                raise serializers.ValidationError(
                    _("Ya tienes una solicitud de este tipo en la última semana.")
                )
        return attrs

    def create(self, validated_data):
        """Create a new solicitud."""
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            validated_data["titular"] = request.user
            # TODO: Calculate fecha_limite based on 30 business days
            # This will be implemented when the calcular_fecha_limite_habil function is created
            from django.utils import timezone
            validated_data["fecha_limite"] = timezone.now()
        return super().create(validated_data)


class SolicitudHabeasDataUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating SolicitudHabeasData (admin only)."""

    class Meta:
        model = SolicitudHabeasData
        fields = [
            "estado",
            "respuesta",
            "motivo_rechazo",
            "evidencia_url",
        ]

    def validate(self, attrs):
        """Validate state transitions and required fields."""
        estado = attrs.get("estado")
        respuesta = attrs.get("respuesta")
        motivo_rechazo = attrs.get("motivo_rechazo")

        if estado == "resuelta" and not respuesta:
            raise serializers.ValidationError({
                "respuesta": _("La respuesta es obligatoria para marcar como resuelta.")
            })

        if estado == "rechazada" and not motivo_rechazo:
            raise serializers.ValidationError({
                "motivo_rechazo": _("El motivo es obligatorio para marcar como rechazada.")
            })

        return attrs


class NotificationSerializer(serializers.ModelSerializer):
    """Serializer for Notification model."""

    leido = serializers.BooleanField(source="leido", read_only=True)
    recipient_email = serializers.EmailField(source="recipient.email", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "recipient",
            "recipient_email",
            "event",
            "tipo",
            "titulo",
            "mensaje",
            "leido",
            "read_at",
            "created_at",
            "repeat_count",
        ]
        read_only_fields = [
            "id",
            "recipient_email",
            "leido",
            "read_at",
            "created_at",
            "repeat_count",
        ]
