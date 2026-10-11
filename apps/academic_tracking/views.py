"""Views for academic tracking."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.academic_tracking.models import AcademicAlert, AcademicRecord
from apps.academic_tracking.serializers import (
    AcademicAlertSerializer,
    AcademicRecordSerializer,
)
from apps.academic_tracking.services import AcademicTrackingService
from apps.accounts.permissions import HasAnyRole

# CAP-011 fine-grained role matrix:
# R-COORD: Coordinador Técnico FODEJAS — día a día del seguimiento
# R-ADMIN: Administrador — acceso completo
# Superusers bypass.


class _AcademicManagementPermission(HasAnyRole):
    """Permission for academic tracking management (R-COORD, R-ADMIN)."""

    def __init__(self):
        # DRF calls permission classes as constructors, so __init__ takes no args
        super().__init__(role_codes=["R-COORD", "R-ADMIN"])

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return request.user.user_roles.filter(role__code__in=self.role_codes).exists()


class AcademicRecordViewSet(viewsets.ModelViewSet):
    """ViewSet for academic records."""

    queryset = AcademicRecord.objects.all()
    serializer_class = AcademicRecordSerializer
    permission_classes = [_AcademicManagementPermission]

    @action(detail=True, methods=["post"])
    def add_grade(self, request, pk=None):
        """Add a grade to the academic record."""
        semester = request.data.get("semester")
        course_name = request.data.get("course_name")
        credits = request.data.get("credits")
        grade = request.data.get("grade")

        if not all([semester, course_name, credits, grade]):
            return Response(
                {"error": "semester, course_name, credits, and grade are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            record = AcademicTrackingService.add_grade(
                pk, semester, course_name, int(credits), float(grade)
            )
            return Response(
                {
                    "status": record.status,
                    "cumulative_average": float(record.cumulative_average),
                }
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def recalculate(self, request, pk=None):
        """Recalculate averages for an academic record."""
        try:
            record = AcademicRecord.objects.get(id=pk)
            AcademicTrackingService.recalculate_averages(record)
            return Response(
                {
                    "status": record.status,
                    "cumulative_average": float(record.cumulative_average),
                }
            )
        except AcademicRecord.DoesNotExist:
            return Response(
                {"error": "Academic record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["post"])
    def graduate(self, request, pk=None):
        """Mark a record as graduated."""
        try:
            record = AcademicTrackingService.mark_graduated(pk)
            return Response({"status": record.status})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AcademicAlertViewSet(viewsets.ModelViewSet):
    """ViewSet for academic alerts."""

    queryset = AcademicAlert.objects.all()
    serializer_class = AcademicAlertSerializer
    permission_classes = [_AcademicManagementPermission]

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Resolve an alert."""
        try:
            alert = AcademicTrackingService.resolve_alert(pk)
            return Response({"status": alert.status})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
