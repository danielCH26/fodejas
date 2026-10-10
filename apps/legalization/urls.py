"""URL configuration for legalization app (CHG-301, CAP-029)."""
from django.urls import path

from apps.legalization.views import (
    LegalizationDetailView,
    LegalizationListView,
    SignDocumentHTMXView,
)

app_name = "legalization"

urlpatterns = [
    path("", LegalizationListView.as_view(), name="list"),
    path(
        "process/<uuid:pk>/",
        LegalizationDetailView.as_view(),
        name="detail",
    ),
    # HTMX signing — form GET and POST.
    path(
        "documents/<uuid:pk>/sign/",
        SignDocumentHTMXView.as_view(),
        name="sign_document",
    ),
]
