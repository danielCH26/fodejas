"""DRF serializers for academic tracking (CHG-401, CAP-011)."""

from rest_framework import serializers

from apps.academic_tracking.models import AcademicAlert, AcademicRecord, GradeEntry


class GradeEntrySerializer(serializers.ModelSerializer):
    """Read representation of a single course grade."""

    class Meta:
        model = GradeEntry
        fields = [
            "id",
            "semester",
            "course_name",
            "credits",
            "grade",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AcademicAlertSerializer(serializers.ModelSerializer):
    """Read representation of an academic alert."""

    class Meta:
        model = AcademicAlert
        fields = [
            "id",
            "alert_type",
            "status",
            "message",
            "created_at",
            "resolved_at",
        ]
        read_only_fields = fields


class AcademicRecordSerializer(serializers.ModelSerializer):
    """Read representation of an academic record with nested data.

    Mutations flow through the ViewSet custom actions, which call
    ``AcademicTrackingService`` directly (design.md: transitions
    validated in the service layer).
    """

    legalization_process = serializers.PrimaryKeyRelatedField(read_only=True)
    grades = GradeEntrySerializer(many=True, read_only=True)
    alerts = AcademicAlertSerializer(many=True, read_only=True)

    class Meta:
        model = AcademicRecord
        fields = [
            "id",
            "legalization_process",
            "status",
            "cumulative_average",
            "semester_count",
            "consecutive_low_semesters",
            "last_reviewed_at",
            "grades",
            "alerts",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
