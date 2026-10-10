"""Serializers for the legalization API (CHG-301, CAP-029)."""
from rest_framework import serializers

from apps.legalization.models import LegalDocument, LegalizationProcess


class LegalDocumentSerializer(serializers.ModelSerializer):
    """Serializer for LegalDocument — read + write."""

    is_signed = serializers.BooleanField(read_only=True)
    can_sign = serializers.SerializerMethodField()

    class Meta:
        model = LegalDocument
        fields = [
            "id",
            "process",
            "document_type",
            "status",
            "pre_sign_hash",
            "post_sign_hash",
            "pdf",
            "signed_at",
            "changes",
            "is_signed",
            "can_sign",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "pre_sign_hash",
            "post_sign_hash",
            "signed_at",
            "changes",
            "is_signed",
            "can_sign",
            "created_at",
            "updated_at",
        ]

    def get_can_sign(self, obj: LegalDocument) -> bool:
        """A document can be signed if it's PENDIENTE and has a PDF."""
        return (
            obj.status == LegalDocument.Status.PENDIENTE
            and obj.pdf
            and bool(obj.pre_sign_hash) is False
        )


class LegalDocumentSignSerializer(serializers.Serializer):
    """Input for POST /<pk>/sign/ — no body required; pk is enough."""

    pass


class LegalDocumentSignResultSerializer(serializers.Serializer):
    """Output from POST /<pk>/sign/."""

    id = serializers.UUIDField()
    document_type = serializers.CharField()
    status = serializers.CharField()
    pre_sign_hash = serializers.CharField()
    post_sign_hash = serializers.CharField()
    signed_at = serializers.DateTimeField()
    provider = serializers.SerializerMethodField()
    pdf_url = serializers.SerializerMethodField()

    def get_provider(self, obj: LegalDocument) -> str:
        return (obj.changes or {}).get("provider", "unknown")

    def get_pdf_url(self, obj: LegalDocument) -> str | None:
        request = self.context.get("request")
        if obj.pdf and request:
            return request.build_absolute_uri(obj.pdf.url)
        return None


class LegalizationProcessSerializer(serializers.ModelSerializer):
    """Serializer for LegalizationProcess."""

    documents = LegalDocumentSerializer(many=True, read_only=True)
    beneficiary_email = serializers.EmailField(
        source="beneficiary.email", read_only=True
    )
    convocatoria_nombre = serializers.CharField(
        source="convocatoria.nombre", read_only=True
    )

    class Meta:
        model = LegalizationProcess
        fields = [
            "id",
            "beneficiary",
            "beneficiary_email",
            "convocatoria",
            "convocatoria_nombre",
            "status",
            "documents",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "beneficiary_email",
            "convocatoria_nombre",
            "created_at",
            "updated_at",
            "completed_at",
        ]
