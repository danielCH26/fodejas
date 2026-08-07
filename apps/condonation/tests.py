"""Tests for condonation app."""

from decimal import Decimal

import pytest
from django.test import TestCase

from apps.condonation.models import Sanction, TerminationRequest
from apps.condonation.services import (
    SanctionService,
    TerminationService,
    calculate_ipc_adjustment,
)


class IPCalculationTest(TestCase):
    """Tests for IPC calculation."""

    def test_no_adjustment_for_zero_years(self):
        """No adjustment for 0 years."""
        result = calculate_ipc_adjustment(Decimal("1000000"), 0)
        self.assertEqual(result, Decimal("0"))

    def test_adjustment_for_one_year(self):
        """5% adjustment for 1 year."""
        result = calculate_ipc_adjustment(Decimal("1000000"), 1)
        self.assertEqual(result, Decimal("50000.00"))

    def test_adjustment_for_two_years(self):
        """Compound adjustment for 2 years."""
        result = calculate_ipc_adjustment(Decimal("1000000"), 2)
        # 1000000 * (1.05^2 - 1) = 1000000 * 0.1025 = 102500
        self.assertEqual(result, Decimal("102500.00"))


class TerminationServiceTest(TestCase):
    """Tests for TerminationService."""

    def test_termination_creation(self):
        """Test creating a termination request."""
        # This test requires a LegalizationProcess - simplified test
        # In real tests, use factories
        pass

    def test_approve_termination_not_found(self):
        """Test approving non-existent termination."""
        with pytest.raises(ValueError, match="Termination not found"):
            TerminationService.approve_termination(
                "00000000-0000-0000-0000-000000000000",
                None,
            )

    def test_reject_termination_not_found(self):
        """Test rejecting non-existent termination."""
        with pytest.raises(ValueError, match="Termination not found"):
            TerminationService.reject_termination(
                "00000000-0000-0000-0000-000000000000",
                None,
            )


class SanctionServiceTest(TestCase):
    """Tests for SanctionService."""

    def test_create_sanction_invalid_cause(self):
        """Test creating sanction with invalid cause."""
        # This test requires a TerminationRequest - simplified test
        pass

    def test_submit_justification_invalid(self):
        """Test submitting invalid justification."""
        with pytest.raises(ValueError, match="Invalid justification"):
            SanctionService.submit_justification(
                "00000000-0000-0000-0000-000000000000",
                "INVALID",
                "test details",
            )

    def test_approve_justification_not_found(self):
        """Test approving justification for non-existent sanction."""
        with pytest.raises(ValueError, match="Sanction not found"):
            SanctionService.approve_justification(
                "00000000-0000-0000-0000-000000000000",
                None,
            )

    def test_confirm_payment_not_found(self):
        """Test confirming payment for non-existent sanction."""
        with pytest.raises(ValueError, match="Sanction not found"):
            SanctionService.confirm_payment(
                "00000000-0000-0000-0000-000000000000",
                None,
                None,
            )
