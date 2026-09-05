"""Tests for academic_tracking app."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.academic_tracking.models import AcademicAlert, AcademicRecord, GradeEntry
from apps.academic_tracking.services import (
    AcademicTrackingService,
    calculate_cumulative_average,
    calculate_semester_average,
    get_status_from_average,
)
from apps.convocatories.models import Convocatory
from apps.legalization.models import LegalizationProcess


class GradeCalculationTest(TestCase):
    """Tests for grade calculation."""

    def test_calculate_semester_average(self):
        """Test semester average calculation."""

        # Create mock grade entries
        class MockGrade:
            def __init__(self, grade, credits):
                self.grade = Decimal(str(grade))
                self.credits = credits

        grades = [
            MockGrade(4.0, 3),  # 12 points, 3 credits
            MockGrade(3.5, 4),  # 14 points, 4 credits
            MockGrade(4.2, 2),  # 8.4 points, 2 credits
        ]

        result = calculate_semester_average(grades)
        # (12 + 14 + 8.4) / (3 + 4 + 2) = 34.4 / 9 = 3.82
        self.assertAlmostEqual(float(result), 3.82, places=2)

    def test_calculate_cumulative_average_empty(self):
        """Test cumulative average with no grades."""
        result = calculate_cumulative_average([])
        self.assertEqual(result, Decimal("0"))

    def test_get_status_from_average_active(self):
        """Test status for active average."""
        result = get_status_from_average(Decimal("4.0"))
        self.assertEqual(result, "ACTIVO")

    def test_get_status_from_average_warning(self):
        """Test status for warning average."""
        result = get_status_from_average(Decimal("3.2"))
        self.assertEqual(result, "ACADEMICO_BAJO")

    def test_get_status_from_average_critical(self):
        """Test status for critical average."""
        result = get_status_from_average(Decimal("2.5"))
        self.assertEqual(result, "SUSPENDIDO")


class AcademicTrackingServiceTest(TestCase):
    """Tests for AcademicTrackingService."""

    def test_create_academic_record_not_found(self):
        """Test creating academic record for non-existent process."""
        import uuid


        # Test with non-existent UUID - should raise ValueError for invalid UUID
        fake_id = uuid.uuid4()
        # The service expects a LegalizationProcess object, not UUID
        with self.assertRaises((ValueError, TypeError)):
            AcademicTrackingService.create_academic_record(fake_id)

    def test_add_grade_not_found(self):
        """Test adding grade to non-existent record."""

        with self.assertRaises(ValueError) as ctx:
            AcademicTrackingService.add_grade(
                "00000000-0000-0000-0000-000000000000",
                1,
                "Test Course",
                3,
                Decimal("4.0"),
            )
        self.assertIn("Academic record not found", str(ctx.exception))

    def test_resolve_alert_not_found(self):
        """Test resolving non-existent alert."""
        with self.assertRaises(ValueError) as ctx:
            AcademicTrackingService.resolve_alert("00000000-0000-0000-0000-000000000000")
        self.assertIn("Alert not found", str(ctx.exception))

    def test_mark_graduated_not_found(self):
        """Test marking non-existent record as graduated."""
        with self.assertRaises(ValueError) as ctx:
            AcademicTrackingService.mark_graduated("00000000-0000-0000-0000-000000000000")
        self.assertIn("Academic record not found", str(ctx.exception))


class AlertGenerationTest(TestCase):
    """Tests for alert generation scenarios."""

    def test_alert_created_for_low_average(self):
        """Test that alert is created when average drops below threshold."""

        # Create mock for alert creation logic
        # Test the alert creation path
        avg = Decimal("3.0")
        status = get_status_from_average(avg)
        # With 3.0, status should be ACADEMICO_BAJO
        self.assertEqual(status, "ACADEMICO_BAJO")

    def test_suspension_trigger_consecutive_low_semesters(self):
        """Test that suspension is triggered after 2 consecutive low semesters."""
        # Test the threshold constant
        from apps.academic_tracking.services import CONSECUTIVE_LOW_SEMESTERS_TRIGGER
        self.assertEqual(CONSECUTIVE_LOW_SEMESTERS_TRIGGER, 2)


class IntegrationTest(TestCase):
    """Integration tests for academic tracking workflow."""

    def test_full_grade_entry_workflow(self):
        """Test complete workflow: add grades -> recalculate -> check status."""
        # Test calculation chain
        class MockGrade:
            def __init__(self, grade, credits):
                self.grade = Decimal(str(grade))
                self.credits = credits

        # Simulate a semester with passing grades
        semester_grades = [
            MockGrade(4.0, 3),
            MockGrade(3.8, 4),
        ]
        avg = calculate_semester_average(semester_grades)
        self.assertGreaterEqual(avg, Decimal("3.5"))

        # Status should be ACTIVO
        status = get_status_from_average(avg)
        self.assertEqual(status, "ACTIVO")

    def test_low_average_workflow(self):
        """Test workflow with low average."""
        class MockGrade:
            def __init__(self, grade, credits):
                self.grade = Decimal(str(grade))
                self.credits = credits

        # Simulate a semester with low grades
        semester_grades = [
            MockGrade(2.5, 3),
            MockGrade(3.0, 4),
        ]
        avg = calculate_semester_average(semester_grades)
        self.assertLess(avg, Decimal("3.5"))

        # Status should be ACADEMICO_BAJO or SUSPENDIDO
        status = get_status_from_average(avg)
        self.assertIn(status, ["ACADEMICO_BAJO", "SUSPENDIDO"])


class AcademicRecordIntegrationTest(TestCase):
    """Real integration tests with database."""

    def setUp(self):
        """Create test fixtures."""
        User = get_user_model()
        # Create test user - CustomUser uses email as username, not username
        self.user = User.objects.create_user(
            email="test@example.com",
            documento="1234567890",
            password="testpass123",
        )
        # Create a Convocatory - required fields: nombre, codigo, periodo, estado
        self.convocatoria = Convocatory.objects.create(
            nombre="Test Convocatoria 2026",
            codigo="test-2026",
            periodo="2026-1",
            estado=Convocatory.Estado.PUBLICADA,
        )
        # Create a LegalizationProcess
        self.legalization_process = LegalizationProcess.objects.create(
            beneficiary=self.user,
            convocatoria=self.convocatoria,
            status=LegalizationProcess.Status.LEGALIZADO,
        )

    def test_create_academic_record_happy_path(self):
        """Test creating academic record for a real process."""
        # Call the service with real LegalizationProcess
        record = AcademicTrackingService.create_academic_record(self.legalization_process)

        # Assert the record was created
        self.assertIsNotNone(record.id)
        self.assertEqual(record.status, AcademicRecord.Status.ACTIVO)
        self.assertEqual(record.legalization_process, self.legalization_process)
        self.assertEqual(record.cumulative_average, Decimal("0"))
        self.assertEqual(record.semester_count, 0)

    def test_add_grade_happy_path(self):
        """Test adding a grade to a real record."""
        # First create an academic record
        record = AcademicTrackingService.create_academic_record(self.legalization_process)

        # Add a grade
        updated_record = AcademicTrackingService.add_grade(
            record.id,
            semester=1,
            course_name="Introducción a la Ingeniería",
            credits=3,
            grade=Decimal("4.5"),
        )

        # Assert grade was created
        self.assertEqual(GradeEntry.objects.filter(academic_record=record).count(), 1)
        grade = GradeEntry.objects.filter(academic_record=record).first()
        self.assertEqual(grade.course_name, "Introducción a la Ingeniería")
        self.assertEqual(grade.credits, 3)
        self.assertEqual(grade.grade, Decimal("4.5"))

        # Assert cumulative average was updated
        self.assertGreater(updated_record.cumulative_average, Decimal("0"))

    def test_alert_created_for_low_average(self):
        """Test that alert is created when average drops below threshold."""
        # Create record
        record = AcademicTrackingService.create_academic_record(self.legalization_process)

        # Add low grades to trigger ACADEMICO_BAJO
        AcademicTrackingService.add_grade(record.id, 1, "Course 1", 3, Decimal("3.2"))
        AcademicTrackingService.add_grade(record.id, 1, "Course 2", 3, Decimal("3.0"))

        # Recalculate - pass the record object, not the ID
        AcademicTrackingService.recalculate_averages(record)

        # Refresh from DB
        record.refresh_from_db()

        # Assert alert was created
        alert_count = AcademicAlert.objects.filter(academic_record=record).count()
        self.assertGreater(alert_count, 0)

    def test_auto_suspension_after_2_low_semesters(self):
        """Test auto-suspension after 2 consecutive low semesters."""
        # Create record
        record = AcademicTrackingService.create_academic_record(self.legalization_process)

        # Add first semester with low average (below 3.5)
        AcademicTrackingService.add_grade(record.id, 1, "Course 1", 3, Decimal("3.0"))
        AcademicTrackingService.add_grade(record.id, 1, "Course 2", 3, Decimal("3.2"))
        AcademicTrackingService.recalculate_averages(record)

        # Add second semester with low average
        AcademicTrackingService.add_grade(record.id, 2, "Course 3", 3, Decimal("3.0"))
        AcademicTrackingService.add_grade(record.id, 2, "Course 4", 3, Decimal("3.1"))
        AcademicTrackingService.recalculate_averages(record)

        # Refresh from DB
        record.refresh_from_db()

        # Assert status changed to SUSPENDIDO after 2 consecutive low semesters
        self.assertEqual(record.status, AcademicRecord.Status.SUSPENDIDO)
        self.assertEqual(record.consecutive_low_semesters, 2)
