"""URL configuration for audit app."""

app_name = "audit"

from django.urls import path

from .views import (
    AuditChainVerifyHtmlView,
    AuditEventDetailView,
    AuditEventListView,
    audit_export,
)

urlpatterns = [
    path("events/", AuditEventListView.as_view(), name="audit-event-list"),
    path("events/<uuid:id>/", AuditEventDetailView.as_view(), name="audit-event-detail"),
    path("verify/", AuditChainVerifyHtmlView.as_view(), name="audit-chain-verify"),
    path("export/", audit_export, name="audit-export"),
]
