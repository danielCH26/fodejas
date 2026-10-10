"""URL routes for the treasury app (CHG-802 / CHG-303 / CAP-010)."""
from django.urls import path

from apps.treasury.views import (
    AuthorizeDisbursementHTMXView,
    DisbursementAuthorizationDetailView,
    DisbursementAuthorizationListView,
    TreasuryReconciliationView,
)

app_name = "treasury"

urlpatterns = [
    # CHG-802 — existing
    path(
        "conciliacion/",
        TreasuryReconciliationView.as_view(),
        name="reconciliation",
    ),
    # CHG-303 Batch B — disbursement authorization
    path(
        "",
        DisbursementAuthorizationListView.as_view(),
        name="disbursement_list",
    ),
    path(
        "<uuid:pk>/",
        DisbursementAuthorizationDetailView.as_view(),
        name="disbursement_detail",
    ),
    path(
        "<uuid:pk>/autorizar/",
        AuthorizeDisbursementHTMXView.as_view(),
        name="authorize",
    ),
]
