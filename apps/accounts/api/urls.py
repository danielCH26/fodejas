"""URLs for accounts API."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.accounts.api.views import (
    ConsentimientoViewSet,
    SolicitudHabeasDataViewSet,
    NotificationViewSet,
)

router = DefaultRouter()
router.register(r"consentimientos", ConsentimientoViewSet, basename="consentimiento")
router.register(r"habeas-data/solicitudes", SolicitudHabeasDataViewSet, basename="solicitud-habeas-data")
router.register(r"notifications", NotificationViewSet, basename="notification")

urlpatterns = [
    path("", include(router.urls)),
]