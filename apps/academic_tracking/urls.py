"""URL configuration for academic_tracking app."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.academic_tracking.views import AcademicAlertViewSet, AcademicRecordViewSet

router = DefaultRouter()
router.register(r"records", AcademicRecordViewSet, basename="academic-record")
router.register(r"alerts", AcademicAlertViewSet, basename="academic-alert")

urlpatterns = [
    path("", include(router.urls)),
]
