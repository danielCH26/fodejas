"""Admin configuration for treasury app."""
from django.contrib import admin
from apps.treasury.models import DisbursementAuthorization


@admin.register(DisbursementAuthorization)
class DisbursementAuthorizationAdmin(admin.ModelAdmin):
    """Admin for DisbursementAuthorization."""

    list_display = [
        "id", "legalization_process", "amount", "status",
        "authorized_by_president", "authorized_by_secretary",
        "treasury_order_number", "paid_at", "created_at"
    ]
    list_filter = ["status", "authorized_by_president", "authorized_by_secretary", "created_at"]
    search_fields = [
        "legalization_process__beneficiary__email",
        "treasury_order_number"
    ]
    readonly_fields = ["created_at", "updated_at", "authorized_at", "paid_at"]
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {
            "fields": ("legalization_process", "amount", "status")
        }),
        ("Autorización", {
            "fields": (
                "authorized_by_president", "authorized_by_secretary",
                "authorized_at"
            )
        }),
        ("Tesorería", {
            "fields": (
                "treasury_order_number", "treasury_order_date",
                "payment_proof", "paid_at"
            )
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at")
        }),
    )
