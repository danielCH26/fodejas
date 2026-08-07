"""URL configuration for condonation app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.condonation.views import SanctionViewSet, TerminationRequestViewSet

router = DefaultRouter()
router.register(r"terminations", TerminationRequestViewSet, basename="termination")
router.register(r"sanctions", SanctionViewSet, basename="sanction")

urlpatterns = [
    path("", include(router.urls)),
]
