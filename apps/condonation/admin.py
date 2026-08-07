"""Admin configuration for condonation app."""

from django.contrib import admin

from apps.condonation.models import Sanction, TerminationRequest


@admin.register(TerminationRequest)
class TerminationRequestAdmin(admin.ModelAdmin):
    """Admin for termination requests."""

    list_display = [
        "id",
        "legalization_process",
        "cause",
        "status",
        "requested_by",
        "reviewed_by",
        "created_at",
    ]
    list_filter = ["status", "cause", "created_at"]
    search_fields = [
        "legalization_process__beneficiary__document",
        "legalization_process__beneficiary__email",
        "description",
    ]
    readonly_fields = ["id", "created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = [
        (
            "Información Principal",
            {
                "fields": [
                    "id",
                    "legalization_process",
                    "cause",
                    "status",
                    "description",
                ]
            },
        ),
        (
            "Usuarios",
            {
                "fields": [
                    "requested_by",
                    "reviewed_by",
                    "reviewed_at",
                ]
            },
        ),
        (
            "Metadatos",
            {
                "fields": [
                    "created_at",
                    "updated_at",
                ]
            },
        ),
    ]


@admin.register(Sanction)
class SanctionAdmin(admin.ModelAdmin):
    """Admin for sanctions."""

    list_display = [
        "id",
        "termination",
        "base_amount",
        "ipc_adjustment",
        "total_amount",
        "status",
        "justification",
        "created_at",
    ]
    list_filter = ["status", "justification", "created_at"]
    search_fields = [
        "termination__legalization_process__beneficiary__document",
        "termination__legalization_process__beneficiary__email",
    ]
    readonly_fields = ["id", "created_at", "updated_at", "total_amount"]
    ordering = ["-created_at"]

    fieldsets = [
        (
            "Información Principal",
            {
                "fields": [
                    "id",
                    "termination",
                    "base_amount",
                    "ipc_adjustment",
                    "total_amount",
                    "status",
                ]
            },
        ),
        (
            "Justificación",
            {
                "fields": [
                    "justification",
                    "justification_details",
                    "justification_approved",
                ]
            },
        ),
        (
            "Pago",
            {
                "fields": [
                    "payment_proof",
                    "paid_at",
                ]
            },
        ),
        (
            "Revisión",
            {
                "fields": [
                    "reviewed_by",
                    "reviewed_at",
                ]
            },
        ),
        (
            "Metadatos",
            {
                "fields": [
                    "created_at",
                    "updated_at",
                ]
            },
        ),
    ]
