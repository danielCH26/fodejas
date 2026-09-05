"""URL configuration for legalization app."""
from django.urls import path

from . import views

app_name = "legalization"

urlpatterns = [
    path("", views.LegalizationDashboardView.as_view(), name="dashboard"),
    path("list/", views.LegalizationListView.as_view(), name="list"),
    path("<uuid:pk>/", views.LegalizationDetailView.as_view(), name="detail"),
    path("document/<uuid:pk>/sign/", views.LegalDocumentSignView.as_view(), name="sign"),
]
