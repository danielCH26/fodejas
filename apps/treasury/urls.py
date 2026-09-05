"""URL configuration for treasury app."""
from django.urls import path

from . import views

app_name = "treasury"

urlpatterns = [
    path("", views.TreasuryDashboardView.as_view(), name="dashboard"),
    path("list/", views.DisbursementListView.as_view(), name="list"),
    path("<uuid:pk>/", views.DisbursementDetailView.as_view(), name="detail"),
    path("<uuid:pk>/authorize/<str:role>/", views.DisbursementAuthorizeView.as_view(), name="authorize"),
    path("<uuid:pk>/confirm/", views.TreasuryConfirmPaymentView.as_view(), name="confirm"),
]
