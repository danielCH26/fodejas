"""URL configuration for reporting (CHG-503)."""

from django.urls import path

from apps.reporting.views import informe_gestion

app_name = "reporting"

urlpatterns = [
    path("gestion/", informe_gestion, name="informe-gestion"),
]
