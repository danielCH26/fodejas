"""URL configuration for audit app."""

app_name = "audit"

from django.urls import path

from .views import (
    AuditChainVerifyView,
    AuditEventDetailView,
    AuditEventListView,
    audit_export,
)

urlpatterns = [
    path("events/", AuditEventListView.as_view(), name="audit-event-list"),
    path("events/<uuid:id>/", AuditEventDetailView.as_view(), name="audit-event-detail"),
    path("export/", audit_export, name="audit-export"),
    # JSON API contract for the /api/ prefix. The HTML page lives at
    # /accounts/audit/verify/ (apps/accounts/urls.py, name "audit_verify").
    path("verify/", AuditChainVerifyView.as_view(), name="audit-chain-verify"),
>>>>>>> chore/audit-verify-url
]
