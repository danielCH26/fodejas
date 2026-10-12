"""URL configuration for Portal de Transparencia API (CHG-504, CAP-021).

Mounted at /api/transparencia/ in config/urls.py.
Read-only, AllowAny — no PII in any response (project.md §14.2,
AGENTS.md §1, Ley 1581/2012).
"""

from django.urls import path

from apps.reporting.views import (
    transparencia_actos,
    transparencia_convocatorias,
    transparencia_estadisticas,
)

app_name = "transparencia_api"

urlpatterns = [
    path("actos/", transparencia_actos, name="actos"),
    path("convocatorias/", transparencia_convocatorias, name="convocatorias"),
    path("estadisticas/", transparencia_estadisticas, name="estadisticas"),
]
