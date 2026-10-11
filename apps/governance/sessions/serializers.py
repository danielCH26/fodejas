"""DRF serializers for governance sessions (CHG-501, CAP-017)."""

from rest_framework import serializers

from apps.governance.sessions.models import (
    ActaSesion,
    MiembroSesion,
    OrdenDelDiaPunto,
    Sesion,
    Voto,
)


class VotoSerializer(serializers.ModelSerializer):
    miembro_sesion = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Voto
        fields = ["id", "miembro_sesion", "valor", "timestamp"]
        read_only_fields = fields


class PuntoSerializer(serializers.ModelSerializer):
    votes = VotoSerializer(many=True, read_only=True)

    class Meta:
        model = OrdenDelDiaPunto
        fields = [
            "id",
            "numero",
            "texto",
            "estado",
            "votes",
        ]
        read_only_fields = fields


class MiembroSesionSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = MiembroSesion
        fields = [
            "id",
            "user",
            "rol",
            "asistencia",
            "es_miembro_cargo",
            "conflicto_declarado",
        ]
        read_only_fields = fields


class ActaSesionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ActaSesion
        fields = [
            "id",
            "pdf_sha256",
            "pre_sign_hash",
            "post_sign_hash",
            "firmantes",
            "estado",
            "signed_at",
        ]
        read_only_fields = fields


class SesionSerializer(serializers.ModelSerializer):
    miembros = MiembroSesionSerializer(many=True, read_only=True)
    puntos = PuntoSerializer(many=True, read_only=True)
    acta = ActaSesionSerializer(read_only=True)

    class Meta:
        model = Sesion
        fields = [
            "id",
            "organo",
            "tipo",
            "fecha_hora",
            "convocatoria_enviada_at",
            "estado",
            "asunto",
            "miembros",
            "puntos",
            "acta",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
