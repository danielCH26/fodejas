"""URL configuration for Portal de Transparencia HTML pages (CHG-504, CAP-021).

Mounted at /transparencia/ in config/urls.py.
Read-only, public (no auth required) — no PII in any response
(project.md §14.2, AGENTS.md §1, Ley 1581/2012).

Uses app_name "transparencia" so {% url 'transparencia:...' %} resolves
in templates. This URLconf is mounted at /transparencia/ while
urls_transparencia.py (API) is at /api/transparencia/ — Django routes
by URL prefix first, so there is no actual namespace conflict.
"""

from django.urls import path

from apps.reporting.views import (
    TransparenciaActosView,
    TransparenciaConvocatoriasView,
    TransparenciaEstadisticasView,
    TransparenciaIndexView,
)

app_name = "transparencia"

urlpatterns = [
    path("", TransparenciaIndexView.as_view(), name="index"),
    path("actos/", TransparenciaActosView.as_view(), name="actos"),
    path("convocatorias/", TransparenciaConvocatoriasView.as_view(), name="convocatorias"),
    path("estadisticas/", TransparenciaEstadisticasView.as_view(), name="estadisticas"),
]
