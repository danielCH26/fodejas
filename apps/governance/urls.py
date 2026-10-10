"""URL configuration for governance HTML views."""

from django.urls import path

from apps.governance.views import (
    ActoCreateView,
    ActoDetailView,
    ActoGeneratePdfView,
    ActoListView,
    ActoModificatorioCreateView,
    ActoPublishView,
    ActoSignView,
    ListadoDefinitivoCreateView,
    ListadoDefinitivoDetailView,
    ListadoPublicoView,
)

app_name = "governance"

urlpatterns = [
    # Actos administrativos
    path("actos/", ActoListView.as_view(), name="acto_list"),
    path("actos/crear/", ActoCreateView.as_view(), name="acto_create"),
    path("actos/<uuid:pk>/", ActoDetailView.as_view(), name="acto_detail"),
    path("actos/<uuid:pk>/generar-pdf/", ActoGeneratePdfView.as_view(), name="acto_generate_pdf"),
    path("actos/<uuid:pk>/publicar/", ActoPublishView.as_view(), name="acto_publish"),
    path("actos/<uuid:pk>/firmar/", ActoSignView.as_view(), name="acto_sign"),
    path(
        "actos/<uuid:pk>/modificatorio/",
        ActoModificatorioCreateView.as_view(),
        name="acto_modificatorio_create",
    ),
    # Listados definitivos
    path("listados/crear/", ListadoDefinitivoCreateView.as_view(), name="listado_create"),
    path("listados/<uuid:pk>/", ListadoDefinitivoDetailView.as_view(), name="listado_detail"),
    # Portal público
    path("resultados/", ListadoPublicoView.as_view(), name="resultados_publicos"),
]
