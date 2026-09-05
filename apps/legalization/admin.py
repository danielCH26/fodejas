"""Admin configuration for legalization app."""
from django.contrib import admin
from apps.legalization.models import LegalDocument, LegalizationProcess


@admin.register(LegalizationProcess)
class LegalizationProcessAdmin(admin.ModelAdmin):
    """Admin for LegalizationProcess."""

    list_display = ["id", "beneficiary", "convocatoria", "status", "created_at", "completed_at"]
    list_filter = ["status", "convocatoria", "created_at"]
    search_fields = ["beneficiary__email", "beneficiary__first_name", "beneficiary__last_name"]
    readonly_fields = ["created_at", "updated_at", "completed_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {
            "fields": ("beneficiary", "convocatoria", "status")
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at", "completed_at")
        }),
    )


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    """Admin for LegalDocument."""

    list_display = ["id", "process", "document_type", "status", "signed_at"]
    list_filter = ["status", "document_type"]
    search_fields = ["process__beneficiary__email"]
    readonly_fields = ["created_at", "updated_at", "signed_at", "pre_sign_hash", "post_sign_hash"]
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {
            "fields": ("process", "document_type", "status")
        }),
        ("Firma", {
            "fields": ("pre_sign_hash", "post_sign_hash", "signed_at")
        }),
        ("Documento", {
            "fields": ("pdf",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )
