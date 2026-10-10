"""Serializers for applications API."""

from rest_framework import serializers

from apps.applications.models import Anexo, Solicitud


class SolicitudSerializer(serializers.ModelSerializer):
    """Serializer for Solicitud model."""

    class Meta:
        model = Solicitud
        fields = [
            "id",
            "uuid",
            "radicado",
            "convocatoria",
            "aspirante",
            "estado",
            "datos_personales",
            "datos_academicos",
            "datos_socioeconomicos",
            "consentimiento",
            "current_step",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "uuid",
            "radicado",
            "estado",
            "created_at",
            "updated_at",
        ]


class SolicitudCreateSerializer(serializers.Serializer):
    """Serializer for creating new solicitudes."""

    convocatoria_id = serializers.IntegerField()


class SolicitudSubmitSerializer(serializers.Serializer):
    """Serializer for submitting a solicitud."""

    consentimiento = serializers.BooleanField()


class AnexoSerializer(serializers.ModelSerializer):
    """Serializer for Anexo model."""

    class Meta:
        model = Anexo
        fields = [
            "id",
            "solicitud",
            "tipo_anexo",
            "archivo",
            "nombre_original",
            "tamano",
            "mime_type",
            "sha256",
            "validado",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "sha256",
            "validado",
            "created_at",
        ]
