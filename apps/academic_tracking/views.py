"""Views for academic tracking (CHG-506, CAP-027)."""

from django.db import transaction
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
from apps.audit.services import log_audit_event

# CAP-011 fine-grained role matrix:
# R-COORD: Coordinador Tecnico FODEJAS - dia a dia del seguimiento
# R-ADMIN: Administrador - acceso completo
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

    @action(detail=True, methods=["patch"])
    def anotar_retorno(self, request, pk=None):
        """Annotate the retorno_archipelago field (CHG-506, CAP-027).

        Body: {"retorno_archipelago": true|false}

        - Strict boolean type check (JSON true/false only; strings or
          numbers -> 400).
        - Permission: _AcademicManagementPermission (R-COORD, R-ADMIN).
        - Audit event: action=academic_retorno_annotate, module=academic_tracking.
          Fail-closed: if log_audit_event raises, return 500 and do NOT save.
        """
        # Strict boolean validation
        raw = request.data.get("retorno_archipelago")
        if not isinstance(raw, bool):
            return Response(
                {"error": "retorno_archipelago debe ser un booleano (true o false)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        value = raw

        # Fetch record
        try:
            record = AcademicRecord.objects.get(pk=pk)
        except AcademicRecord.DoesNotExist:
            return Response(
                {"error": "Academic record not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Fail-closed + atomic: audit event and annotation commit or roll
        # back together (CAP-022 convention: never swallow audit errors).
        with transaction.atomic():
            log_audit_event(
                actor=request.user,
                action="academic_retorno_annotate",
                entity="academicrecord",
                entity_id=record.id,
                changes={"after": {"retorno_archipelago": value}},
                module="academic_tracking",
            )
            record.retorno_archipelago = value
            record.save(update_fields=["retorno_archipelago"])
        return Response({"retorno_archipelago": value})


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
