"""Admin for treasury app (CHG-303, CAP-010)."""

from django.contrib import admin

from apps.treasury.models import DisbursementAuthorization


@admin.register(DisbursementAuthorization)
class DisbursementAuthorizationAdmin(admin.ModelAdmin):
    """Admin for DisbursementAuthorization (CAP-010).

    Task 7.1: list_display (status, process, amount, dates),
    list_filter by status, search by order number / beneficiary.
    """

    list_display = [
        "id",
        "status",
        "legalization_process",
        "amount",
        "created_at",
        "authorized_at",
        "treasury_order_date",
        "paid_at",
    ]
    list_filter = [
        "status",
        ("treasury_order_date", admin.DateFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
    ]
    search_fields = [
        "treasury_order_number",
        "legalization_process__beneficiary__email",
        "legalization_process__beneficiary__documento",
    ]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "authorized_at",
        "treasury_received_at",
        "paid_at",
        "treasury_order_attachments",
    ]
    ordering = ["-created_at"]
    autocomplete_fields = [
        "legalization_process",
        "authorized_by_president",
        "authorized_by_secretary",
    ]
