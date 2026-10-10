"""URL configuration for applications API."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import SolicitudViewSet

router = DefaultRouter()
router.register(r"solicitudes", SolicitudViewSet, basename="solicitud")

urlpatterns = [
    path("", include(router.urls)),
]
