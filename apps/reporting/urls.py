"""URL configuration for reporting (CHG-503) and Portal de Transparencia (CHG-504)."""

from django.urls import path

from apps.reporting.views import (
    informe_gestion,
    transparencia_actos,
    transparencia_convocatorias,
    transparencia_estadisticas,
)

app_name = "reporting"

urlpatterns = [
    # Internal management reports (CHG-503)
    path("gestion/", informe_gestion, name="informe-gestion"),
    # Public transparency portal API (CHG-504)
    path("transparencia/actos/", transparencia_actos, name="transparencia-actos"),
    path("transparencia/convocatorias/", transparencia_convocatorias, name="transparencia-convocatorias"),
    path("transparencia/estadisticas/", transparencia_estadisticas, name="transparencia-estadisticas"),
]
