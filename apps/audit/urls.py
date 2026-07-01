"""URL configuration for audit app."""
from django.urls import path

from .views import AuditChainVerifyView, AuditEventDetailView, AuditEventListView

urlpatterns = [
    path("events/", AuditEventListView.as_view(), name="audit-event-list"),
    path("events/<uuid:id>/", AuditEventDetailView.as_view(), name="audit-event-detail"),
    path("verify/", AuditChainVerifyView.as_view(), name="audit-chain-verify"),
]
