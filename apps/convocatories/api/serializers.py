"""Serializers for Convocatory API."""

from django.utils.translation import gettext as _

from rest_framework import serializers

from apps.convocatories.domain import Estado, get_transiciones_disponibles
from apps.convocatories.models import Convocatory


class ConvocatorySerializer(serializers.ModelSerializer):
    """Serializer for Convocatory model."""

    estado_display = serializers.CharField(source="get_estado_display", read_only=True)
    transiciones_disponibles = serializers.SerializerMethodField()

    class Meta:
        model = Convocatory
        fields = [
            "id",
            "codigo",
            "nombre",
            "tipo",
            "periodo",
            "estado",
            "estado_display",
            "transiciones_disponibles",
            "fecha_publicacion",
            "fecha_apertura",
            "fecha_cierre",
            "created_at",
        ]
        read_only_fields = ["id", "codigo", "created_at"]

    def get_transiciones_disponibles(self, obj):
        """Get available transitions from current state."""
        return list(get_transiciones_disponibles(obj.estado))


class TransitionSerializer(serializers.Serializer):
    """Serializer for state transitions."""

    destino = serializers.ChoiceField(
        choices=[
            (Estado.PUBLICADA, "Publicada"),
            (Estado.EN_INSCRIPCION, "En Inscripción"),
            (Estado.EN_VERIFICACION, "En Verificación"),
            (Estado.EN_CALIFICACION, "En Calificación"),
            (Estado.DEFINITIVA, "Definitiva"),
            (Estado.CERRADA, "Cerrada"),
            (Estado.CANCELADA, "Cancelada"),
        ]
    )
    motivo = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        """Validate transition is allowed."""
        from django.core.exceptions import ValidationError

        from apps.convocatories.domain import validar_transicion

        estado_origen = self.instance.estado if self.instance else ""
        estado_destino = attrs.get("destino")

        es_valida, error_code = validar_transicion(estado_origen, estado_destino)

        if not es_valida:
            raise ValidationError(
                {"destino": _("Transición no permitida: %(estado_origen)s → %(estado_destino)s")
                % {"estado_origen": estado_origen, "estado_destino": estado_destino}}
            )

        # Require motivo for CANCELADA
        if estado_destino == Estado.CANCELADA and not attrs.get("motivo"):
            raise ValidationError({"motivo": _("El motivo es requerido para cancelar")})

        return attrs
