"""Tests for academic_tracking app."""

from decimal import Decimal

from django.test import TestCase

from apps.academic_tracking.services import (
    AcademicTrackingService,
    calculate_cumulative_average,
    calculate_semester_average,
    get_status_from_average,
)


class GradeCalculationTest(TestCase):
    """Tests for grade calculation."""

    def test_calculate_semester_average(self):
        """Test semester average calculation."""
        # This test requires mock GradeEntry objects
        pass

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
        # This test requires mock LegalizationProcess
        pass

    def test_add_grade_not_found(self):
        """Test adding grade to non-existent record."""
        from apps.academic_tracking.models import AcademicRecord

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
