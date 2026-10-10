"""URL configuration for applications HTML views."""
from django.urls import path

from apps.applications.views import (
    ApplicationApplyView,
    ApplicationDetailView,
    ApplicationListView,
    ApplicationUploadView,
    ApplicationWizardStepView,
    ApplicationWizardView,
    RequirementApproveView,
    RequirementHistoryView,
    RequirementRejectView,
    RequirementReviewDetailView,
    # Review views (CHG-203)
    RequirementReviewListView,
    RequirementVerifyView,
)

app_name = "applications"

urlpatterns = [
    # Apply to convocation
    path("apply/<uuid:pk>/", ApplicationApplyView.as_view(), name="apply"),

    # List view
    path("", ApplicationListView.as_view(), name="list"),

    # Detail view with UUID
    path("<uuid:pk>/", ApplicationDetailView.as_view(), name="detail"),

    # Wizard views
    path("<uuid:pk>/wizard/", ApplicationWizardView.as_view(), name="wizard"),
    path(
        "<uuid:pk>/wizard/<int:step>/",
        ApplicationWizardStepView.as_view(),
        name="wizard_step"
    ),

    # Upload view
    path(
        "<uuid:pk>/upload/",
        ApplicationUploadView.as_view(),
        name="upload"
    ),

    # Review views (CHG-203)
    path("revision/", RequirementReviewListView.as_view(), name="review_list"),
    path("revision/<uuid:pk>/", RequirementReviewDetailView.as_view(), name="review_detail"),
    path("revision/<uuid:pk>/verificar/", RequirementVerifyView.as_view(), name="review_verify"),
    path("revision/<uuid:pk>/aprobar/", RequirementApproveView.as_view(), name="review_approve"),
    path("revision/<uuid:pk>/rechazar/", RequirementRejectView.as_view(), name="review_reject"),
    path("revision/<uuid:pk>/historial/", RequirementHistoryView.as_view(), name="review_history"),
]
