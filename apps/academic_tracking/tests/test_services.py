"""Unit and workflow tests for AcademicTrackingService (CHG-401, CAP-011).

Covers Art. 16 Decreto 0372/2025: minimum 3.5 average requirement,
weighted cumulative averages, consecutive-low-semester suspension
trigger, alert generation and graduation.
"""

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.academic_tracking.models import AcademicAlert, AcademicRecord, GradeEntry
from apps.academic_tracking.services import (
    AcademicTrackingService,
    calculate_cumulative_average,
    calculate_semester_average,
    get_status_from_average,
)
from apps.audit.models import AuditEvent
from apps.convocatories.models import Convocatory
from apps.legalization.models import LegalizationProcess

User = get_user_model()


def _make_user(n, staff=False):
    return User.objects.create_user(
        email=f"synthetic-acad-{n}-{n * 3}@example.test",
        documento=f"3456789{n:04d}",
        password="test-password-not-real",
        first_name="Aspirante",
        last_name="Ejemplo",
        is_staff=staff,
        is_superuser=staff,
    )


def _make_legalized_process(n):
    beneficiary = _make_user(100 + n)
    conv = Convocatory.objects.create(
        nombre=f"Conv CHG-401 {n}",
        estado=Convocatory.Estado.EN_INSCRIPCION,
    )
    return LegalizationProcess.objects.create(
        beneficiary=beneficiary,
        convocatoria=conv,
        status=LegalizationProcess.Status.LEGALIZADO,
    )


@pytest.fixture
def reviewer(db):
    return _make_user(1, staff=True)


@pytest.fixture
def record(db):
    return AcademicTrackingService.create_academic_record(_make_legalized_process(1))


def _grade(record, semester, course, credits, grade):
    return AcademicTrackingService.add_grade(
        record.id, semester, course, credits, Decimal(str(grade))
    )


class TestAverages:
    def test_semester_average_is_credit_weighted(self, db):
        """(4.0*3 + 5.0*2) / 5 = 22/5 = 4.40 (weighted by credits)."""
        grades = [
            GradeEntry(semester=1, course_name="A", credits=3, grade=Decimal("4.0")),
            GradeEntry(semester=1, course_name="B", credits=2, grade=Decimal("5.0")),
        ]
        assert calculate_semester_average(grades) == Decimal("4.40")

    def test_semester_average_empty_is_zero(self, db):
        assert calculate_semester_average([]) == Decimal("0")

    def test_cumulative_average_merges_all_semesters(self, db):
        """Semester 1 avg 3.0 (3cr), semester 2 avg 5.0 (3cr) -> 4.00."""
        grades = [
            GradeEntry(semester=1, course_name="A", credits=3, grade=Decimal("3.0")),
            GradeEntry(semester=2, course_name="B", credits=3, grade=Decimal("5.0")),
        ]
        assert calculate_cumulative_average(grades) == Decimal("4.00")

    def test_status_thresholds_per_design(self, db):
        assert get_status_from_average(Decimal("3.5")) == AcademicRecord.Status.ACTIVO
        assert get_status_from_average(Decimal("3.2")) == AcademicRecord.Status.ACADEMICO_BAJO
        assert get_status_from_average(Decimal("2.9")) == AcademicRecord.Status.SUSPENDIDO


@pytest.mark.django_db
class TestAcademicTrackingService:
    def test_create_record_links_legalized_process(self, record):
        assert record.status == AcademicRecord.Status.ACTIVO
        assert record.cumulative_average == Decimal("0")

    def test_add_grade_recalculates_and_is_idempotent(self, record):
        _grade(record, 1, "Cálculo", 3, 4.0)
        result = _grade(record, 1, "Cálculo", 3, 5.0)  # same course: update
        record.refresh_from_db()
        assert record.grades.count() == 1
        assert record.grades.first().grade == Decimal("5.0")
        assert record.cumulative_average == Decimal("5.00")
        assert record.semester_count == 1
        assert result.id == record.id

    def test_two_low_consecutive_semesters_auto_suspend(self, record):
        """Art. 16 trigger: 2 consecutive semesters below 3.5 suspend."""
        _grade(record, 1, "Materia A", 3, 3.0)
        _grade(record, 2, "Materia B", 3, 3.2)
        record.refresh_from_db()
        assert record.consecutive_low_semesters == 2
        assert record.status == AcademicRecord.Status.SUSPENDIDO
        assert AcademicAlert.objects.filter(
            academic_record=record,
            alert_type=AcademicAlert.AlertType.SUSPENSION,
        ).exists()

    def test_low_then_high_semester_does_not_suspend(self, record):
        _grade(record, 1, "Materia A", 3, 3.0)
        _grade(record, 2, "Materia B", 3, 4.5)
        record.refresh_from_db()
        assert record.consecutive_low_semesters == 0
        assert record.status == AcademicRecord.Status.ACTIVO

    def test_warning_zone_creates_bajo_rendimiento_alert(self, record):
        _grade(record, 1, "Materia A", 3, 3.2)
        record.refresh_from_db()
        assert record.status == AcademicRecord.Status.ACADEMICO_BAJO
        assert AcademicAlert.objects.filter(
            academic_record=record,
            alert_type=AcademicAlert.AlertType.BAJO_RENDIMIENTO,
        ).exists()

    def test_resolve_alert(self, record):
        alert = AcademicTrackingService.create_alert(
            record, AcademicAlert.AlertType.PROBACION, "Sintético"
        )
        result = AcademicTrackingService.resolve_alert(alert.id)
        assert result.status == AcademicAlert.Status.RESUELTA
        assert result.resolved_at is not None

    def test_mark_graduated(self, record):
        result = AcademicTrackingService.mark_graduated(record.id)
        assert result.status == AcademicRecord.Status.GRADUADO
        assert AcademicAlert.objects.filter(
            academic_record=record,
            alert_type=AcademicAlert.AlertType.GRADUACION,
        ).exists()

    def test_add_grade_rejects_unknown_record(self, db):
        import uuid

        with pytest.raises(ValueError, match="not found"):
            AcademicTrackingService.add_grade(uuid.uuid4(), 1, "X", 3, Decimal("4.0"))


@pytest.mark.django_db
class TestAuditTrail:
    def test_graduation_writes_audit_event(self, record, reviewer):
        AcademicTrackingService.mark_graduated(record.id)
        assert AuditEvent.objects.filter(
            module="academic_tracking", entity="academic_record"
        ).exists()

    def test_suspension_writes_audit_event(self, record):
        _grade(record, 1, "Materia A", 3, 3.0)
        _grade(record, 2, "Materia B", 3, 3.1)
        assert (
            AuditEvent.objects.filter(
                module="academic_tracking",
                entity="academic_record",
                action="UPDATE",
            ).count()
            >= 1
        )
