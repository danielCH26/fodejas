"""URL configuration for governance sessions (CHG-501)."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.governance.sessions.views import ActaViewSet, SesionViewSet

router = DefaultRouter()
router.register(r"sessions", SesionViewSet, basename="session")
router.register(r"actas", ActaViewSet, basename="session-acta")

urlpatterns = [
    path("", include(router.urls)),
]
