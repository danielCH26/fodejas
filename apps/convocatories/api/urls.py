"""URL configuration for Convocatory API."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import ConvocatoryViewSet

router = DefaultRouter()
router.register(r"convocatorias", ConvocatoryViewSet, basename="convocatoria")

urlpatterns = [
    path("", include(router.urls)),
]
