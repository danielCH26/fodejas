"""URL configuration for convocatories app."""
from django.urls import path

from .views import (
    ConvocatoryCreateView,
    ConvocatoryDetailView,
    ConvocatoryListView,
    ConvocatoryTransitionView,
    ConvocatoryUpdateView,
)

app_name = "convocatories"

urlpatterns = [
    path("", ConvocatoryListView.as_view(), name="list"),
    path("crear/", ConvocatoryCreateView.as_view(), name="create"),
    path("<uuid:pk>/", ConvocatoryDetailView.as_view(), name="detail"),
    path("<uuid:pk>/editar/", ConvocatoryUpdateView.as_view(), name="update"),
    path(
        "<uuid:pk>/transicionar/",
        ConvocatoryTransitionView.as_view(),
        name="transition",
    ),
]
