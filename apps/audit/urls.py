"""URL configuration for audit app."""
from django.urls import path

from .views import (
    AuditChainVerifyHtmlView,
    AuditEventDetailHtmlView,  # HTML view, not DRF
    AuditEventListView,
)

urlpatterns = [
    path("events/", AuditEventListView.as_view(), name="audit-event-list"),
    path("events/<uuid:id>/", AuditEventDetailHtmlView.as_view(), name="audit-event-detail"),
    path("verify/", AuditChainVerifyHtmlView.as_view(), name="audit-chain-verify"),
]
