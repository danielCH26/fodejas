"""URLs for the legalization API (CHG-301, CAP-029)."""
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.legalization.api.views import LegalDocumentViewSet, LegalizationProcessViewSet

router = DefaultRouter()
router.register(r"processes", LegalizationProcessViewSet, basename="legalization-process")
router.register(r"documents", LegalDocumentViewSet, basename="legalization-document")

urlpatterns = [
    path("", include(router.urls)),
]
