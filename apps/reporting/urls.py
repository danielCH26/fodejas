"""URL configuration for reporting (CHG-503, CHG-506)."""

from django.urls import path

from apps.reporting.views import estudio_impacto_view, informe_gestion

app_name = "reporting"

urlpatterns = [
    path("gestion/", informe_gestion, name="informe-gestion"),
    path("estudio-impacto/", estudio_impacto_view, name="estudio-impacto"),
]
