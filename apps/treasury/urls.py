"""URL routes for the treasury app (CHG-802 / CAP-010)."""
from django.urls import path

from apps.treasury.views import TreasuryReconciliationView


app_name = "treasury"

urlpatterns = [
    path(
        "conciliacion/",
        TreasuryReconciliationView.as_view(),
        name="reconciliation",
    ),
]
