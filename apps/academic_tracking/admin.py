"""Admin configuration for academic_tracking app."""

from django.contrib import admin

from apps.academic_tracking.models import AcademicAlert, AcademicRecord, GradeEntry


@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    """Admin for academic records."""

    list_display = [
        "id",
        "legalization_process",
        "status",
        "cumulative_average",
        "semester_count",
        "consecutive_low_semesters",
        "updated_at",
    ]
    list_filter = ["status", "semester_count"]
    search_fields = [
        "legalization_process__beneficiary__document",
        "legalization_process__beneficiary__email",
    ]
    readonly_fields = ["id", "created_at", "updated_at", "cumulative_average"]
    ordering = ["-updated_at"]


@admin.register(GradeEntry)
class GradeEntryAdmin(admin.ModelAdmin):
    """Admin for grade entries."""

    list_display = [
        "id",
        "academic_record",
        "semester",
        "course_name",
        "credits",
        "grade",
    ]
    list_filter = ["semester", "academic_record__status"]
    search_fields = ["course_name", "academic_record__legalization_process__beneficiary__email"]
    ordering = ["-semester", "course_name"]


@admin.register(AcademicAlert)
class AcademicAlertAdmin(admin.ModelAdmin):
    """Admin for academic alerts."""

    list_display = [
        "id",
        "academic_record",
        "alert_type",
        "status",
        "created_at",
    ]
    list_filter = ["alert_type", "status", "created_at"]
    search_fields = ["message", "academic_record__legalization_process__beneficiary__email"]
    readonly_fields = ["id", "created_at"]
    ordering = ["-created_at"]
