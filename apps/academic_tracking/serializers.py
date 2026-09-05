"""Serializers for academic tracking API."""
from rest_framework import serializers

from apps.academic_tracking.models import AcademicAlert, AcademicRecord, GradeEntry


class GradeEntrySerializer(serializers.ModelSerializer):
    """Serializer for GradeEntry model."""

    class Meta:
        model = GradeEntry
        fields = [
            "id", "semester", "course_name", "credits", "grade",
            "created_at", "updated_at"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AcademicRecordSerializer(serializers.ModelSerializer):
    """Serializer for AcademicRecord model."""

    grades = GradeEntrySerializer(many=True, read_only=True)
    legalization_process = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = AcademicRecord
        fields = [
            "id", "legalization_process", "status", "cumulative_average",
            "semester_count", "consecutive_low_semesters", "last_reviewed_at",
            "created_at", "updated_at", "grades"
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AcademicAlertSerializer(serializers.ModelSerializer):
    """Serializer for AcademicAlert model."""

    academic_record = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = AcademicAlert
        fields = [
            "id", "academic_record", "alert_type", "status", "message",
            "created_at", "resolved_at"
        ]
        read_only_fields = ["id", "created_at"]


class GradeEntryCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating grades."""

    semester = serializers.IntegerField(min_value=1)
    course_name = serializers.CharField(max_length=200)
    credits = serializers.IntegerField(min_value=1)
    grade = serializers.DecimalField(max_digits=3, decimal_places=2, min_value=0, max_value=5.0)


class AcademicRecordCreateSerializer(serializers.Serializer):
    """Serializer for creating academic record."""

    legalization_process_id = serializers.UUIDField()
