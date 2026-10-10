"""Django admin for Legalization models (CHG-301, CAP-029)."""
from django.contrib import admin

from apps.legalization.models import LegalDocument, LegalizationProcess


@admin.register(LegalizationProcess)
class LegalizationProcessAdmin(admin.ModelAdmin):
    """Admin for LegalizationProcess."""

    list_display = [
        "id",
        "beneficiary",
        "convocatoria",
        "status",
        "created_at",
        "completed_at",
    ]
    list_filter = ["status", "created_at"]
    search_fields = ["beneficiary__email", "convocatoria__nombre", "convocatoria__codigo"]
    readonly_fields = ["id", "created_at", "updated_at", "completed_at"]
    autocomplete_fields = ["beneficiary", "convocatoria"]


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    """Admin for LegalDocument — shows hash fields read-only."""

    list_display = [
        "id",
        "document_type",
        "status",
        "pre_sign_hash_short",
        "post_sign_hash_short",
        "signed_at",
        "provider_badge",
    ]
    list_filter = ["status", "document_type", "created_at"]
    search_fields = [
        "id",
        "process__beneficiary__email",
        "process__convocatoria__nombre",
    ]
    readonly_fields = [
        "id",
        "pre_sign_hash",
        "post_sign_hash",
        "signed_at",
        "changes",
        "created_at",
        "updated_at",
    ]
    autocomplete_fields = ["process"]

    fieldsets = [
        (
            None,
            {
                "fields": [
                    "id",
                    "process",
                    "document_type",
                    "status",
                    "pdf",
                ]
            },
        ),
        (
            "Firma electrónica (CHG-301)",
            {
                "fields": [
                    "pre_sign_hash",
                    "post_sign_hash",
                    "signed_at",
                    "changes",
                ],
                "description": (
                    "Los campos de firma son de solo lectura. "
                    "Use /api/legalization/documents/<id>/sign/ para firmar."
                ),
            },
        ),
        ("Metadatos", {"fields": ["created_at", "updated_at"]}),
    ]

    @admin.display(description="Pre-hash", ordering="pre_sign_hash")
    def pre_sign_hash_short(self, obj):
        if obj.pre_sign_hash:
            return f"{obj.pre_sign_hash[:16]}…"
        return "—"

    @admin.display(description="Post-hash", ordering="post_sign_hash")
    def post_sign_hash_short(self, obj):
        if obj.post_sign_hash:
            return f"{obj.post_sign_hash[:16]}…"
        return "—"

    @admin.display(description="Provider")
    def provider_badge(self, obj):
        prov = (obj.changes or {}).get("provider", None)
        if prov:
            color = "green" if prov == "local" else "gray"
            return f'<span style="color:{color}">{prov}</span>'
        return "—"

    provider_badge.allow_tags = True
