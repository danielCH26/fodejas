"""URL configuration for claims HTML views."""
from django.urls import path

from apps.claims.views import (
    ReclamacionAdminListView,
    ReclamacionCreateView,
    ReclamacionDetailView,
    ReclamacionListView,
    ReclamacionResolveView,
    ReclamacionUpdateView,
    ApelacionListView,
    ApelacionCreateView,
    ApelacionDetailView,
    ApelacionTransitionView,
    ApelacionAdminListView,
)

app_name = "claims"

urlpatterns = [
    # User views
    path("", ReclamacionListView.as_view(), name="list"),
    path("crear/<uuid:solicitud_uuid>/", ReclamacionCreateView.as_view(), name="create"),
    path("<uuid:pk>/", ReclamacionDetailView.as_view(), name="detail"),
    path("<uuid:pk>/editar/", ReclamacionUpdateView.as_view(), name="edit"),
    
    # Admin/Junta views
    path("admin/", ReclamacionAdminListView.as_view(), name="admin_list"),
    path("admin/<uuid:pk>/resolver/", ReclamacionResolveView.as_view(), name="resolve"),
    
    # Apelacion views (CHG-206)
    path("apelaciones/", ApelacionListView.as_view(), name="apelacion_list"),
    path("apelaciones/crear/<uuid:reclamacion_uuid>/", ApelacionCreateView.as_view(), name="apelacion_create"),
    path("apelaciones/<uuid:pk>/", ApelacionDetailView.as_view(), name="apelacion_detail"),
    path("apelaciones/<uuid:pk>/analisis/", ApelacionTransitionView.as_view(), name="apelacion_analisis"),
    path("apelaciones/<uuid:pk>/confirmar/", ApelacionTransitionView.as_view(), name="apelacion_confirmar"),
    path("apelaciones/<uuid:pk>/revocar/", ApelacionTransitionView.as_view(), name="apelacion_revocar"),
    path("apelaciones/admin/", ApelacionAdminListView.as_view(), name="apelacion_admin_list"),
]
