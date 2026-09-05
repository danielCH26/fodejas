"""Services for academic tracking."""

from datetime import UTC, datetime
from decimal import Decimal

from django.db import transaction

from apps.academic_tracking.models import AcademicAlert, AcademicRecord, GradeEntry

# Threshold constants per Art. 16 Decreto 0372/2025
MIN_AVERAGE = Decimal("3.5")
WARNING_THRESHOLD = Decimal("3.0")
CRITICAL_THRESHOLD = Decimal("3.0")
CONSECUTIVE_LOW_SEMESTERS_TRIGGER = 2


def calculate_semester_average(grades: list[GradeEntry]) -> Decimal:
    """Calculate weighted average for a semester.

    Args:
        grades: List of GradeEntry for a semester

    Returns:
        Weighted average (grade * credits) / total credits
    """
    if not grades:
        return Decimal("0")

    total_points = sum(g.grade * g.credits for g in grades)
    total_credits = sum(g.credits for g in grades)

    if total_credits == 0:
        return Decimal("0")

    return (total_points / total_credits).quantize(Decimal("0.01"))


def calculate_cumulative_average(grades: list[GradeEntry]) -> Decimal:
    """Calculate cumulative weighted average across all semesters.

    Args:
        grades: List of all GradeEntry for an academic record

    Returns:
        Cumulative weighted average
    """
    if not grades:
        return Decimal("0")

    return calculate_semester_average(grades)


def get_status_from_average(average: Decimal) -> str:
    """Determine academic status from average.

    Args:
        average: Cumulative average

    Returns:
        Status string
    """
    if average >= MIN_AVERAGE:
        return AcademicRecord.Status.ACTIVO
    elif average >= CRITICAL_THRESHOLD:
        return AcademicRecord.Status.ACADEMICO_BAJO
    else:
        return AcademicRecord.Status.SUSPENDIDO


class AcademicTrackingService:
    """Service for managing academic tracking."""

    @staticmethod
    def create_academic_record(legalization_process):
        """Create a new academic record for a legalized process.

        Args:
            legalization_process: LegalizationProcess instance

        Returns:
            AcademicRecord instance
        """
        record = AcademicRecord.objects.create(
            legalization_process=legalization_process,
            status=AcademicRecord.Status.ACTIVO,
        )
        return record

    @staticmethod
    @transaction.atomic
    def add_grade(record_id, semester, course_name, credits, grade):
        """Add a grade entry and recalculate averages.

        Args:
            record_id: AcademicRecord ID
            semester: Semester number
            course_name: Course name
            credits: Course credits
            grade: Grade (0-5)

        Returns:
            Updated AcademicRecord instance
        """
        try:
            record = AcademicRecord.objects.get(id=record_id)
        except AcademicRecord.DoesNotExist:
            raise ValueError("Academic record not found") from None

        # Create grade entry
        grade_entry, created = GradeEntry.objects.update_or_create(
            academic_record=record,
            semester=semester,
            course_name=course_name,
            defaults={
                "credits": credits,
                "grade": grade,
            },
        )

        # Recalculate averages
        AcademicTrackingService.recalculate_averages(record)

        return record

    @staticmethod
    @transaction.atomic
    def recalculate_averages(record: AcademicRecord):
        """Recalculate semester and cumulative averages.

        Args:
            record: AcademicRecord instance
        """
        # Get all grades ordered by semester
        grades = list(record.grades.all())

        # Calculate cumulative average
        cumulative_avg = calculate_cumulative_average(grades)
        record.cumulative_average = cumulative_avg

        # Get semester count
        semesters = {g.semester for g in grades}
        record.semester_count = len(semesters)

        # Calculate consecutive low semesters
        consecutive_low = 0
        for sem in sorted(semesters, reverse=True):
            sem_grades = [g for g in grades if g.semester == sem]
            sem_avg = calculate_semester_average(sem_grades)
            if sem_avg < MIN_AVERAGE:
                consecutive_low += 1
            else:
                break
        record.consecutive_low_semesters = consecutive_low

        # Update status based on average and consecutive lows
        new_status = get_status_from_average(cumulative_avg)

        # Check for automatic suspension trigger
        if consecutive_low >= CONSECUTIVE_LOW_SEMESTERS_TRIGGER:
            new_status = AcademicRecord.Status.SUSPENDIDO
            AcademicTrackingService.create_alert(
                record,
                AcademicAlert.AlertType.SUSPENSION,
                f"Suspensión automática: {consecutive_low} semestres consecutivos bajo 3.5",
            )

        record.status = new_status
        record.last_reviewed_at = datetime.now(UTC)
        record.save()

        # Create alert if status changed to academic bajo
        if new_status == AcademicRecord.Status.ACADEMICO_BAJO:
            AcademicTrackingService.create_alert(
                record,
                AcademicAlert.AlertType.BAJO_RENDIMIENTO,
                f"Bajo rendimiento: promedio acumulado {cumulative_avg}",
            )

    @staticmethod
    def create_alert(record, alert_type, message):
        """Create an academic alert.

        Args:
            record: AcademicRecord instance
            alert_type: Alert type
            message: Alert message

        Returns:
            AcademicAlert instance
        """
        alert = AcademicAlert.objects.create(
            academic_record=record,
            alert_type=alert_type,
            message=message,
        )
        return alert

    @staticmethod
    def resolve_alert(alert_id):
        """Mark an alert as resolved.

        Args:
            alert_id: AcademicAlert ID

        Returns:
            Updated AcademicAlert instance
        """
        try:
            alert = AcademicAlert.objects.get(id=alert_id)
        except AcademicAlert.DoesNotExist:
            raise ValueError("Alert not found") from None

        alert.status = AcademicAlert.Status.RESUELTA
        alert.resolved_at = datetime.now(UTC)
        alert.save()
        return alert

    @staticmethod
    def mark_graduated(record_id):
        """Mark a record as graduated.

        Args:
            record_id: AcademicRecord ID

        Returns:
            Updated AcademicRecord instance
        """
        try:
            record = AcademicRecord.objects.get(id=record_id)
        except AcademicRecord.DoesNotExist:
            raise ValueError("Academic record not found") from None

        record.status = AcademicRecord.Status.GRADUADO
        record.save()

        AcademicTrackingService.create_alert(
            record,
            AcademicAlert.AlertType.GRADUACION,
            "El beneficiario ha completado sus estudios",
        )

        return record
