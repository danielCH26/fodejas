"""Unit and workflow tests for TerminationService and SanctionService (CHG-304).

Covers Art. 14/15/17 Decreto 0372/2025 flows: termination causes,
automatic sanction for fraud causes, 30-calendar-day justification
window (Art. 17), condonation and payment confirmation.
"""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.condonation.models import Sanction, TerminationRequest
from apps.condonation.services import (
    SanctionService,
    TerminationService,
    calculate_ipc_adjustment,
)
from apps.convocatories.models import Convocatory
from apps.legalization.models import LegalizationProcess

User = get_user_model()


def _make_user(**extra):
    return User.objects.create_user(
        email=f"synthetic-{User.objects.count() + 1}-{pytest.__name__}@example.test",
        documento=f"1234567{User.objects.count() + 1:04d}",
        password="test-password-not-real",
        first_name="Aspirante",
        last_name="Ejemplo",
        **extra,
    )


def _make_legalized_process(beneficiary):
    conv = Convocatory.objects.create(
        nombre="Test Convocatoria CHG-304",
        estado=Convocatory.Estado.EN_INSCRIPCION,
    )
    return LegalizationProcess.objects.create(
        beneficiary=beneficiary,
        convocatoria=conv,
        status=LegalizationProcess.Status.LEGALIZADO,
    )


@pytest.fixture
def reviewer(db):
    return _make_user(is_staff=True, is_superuser=True)


@pytest.fixture
def legalized_process(db):
    beneficiary = _make_user()
    return _make_legalized_process(beneficiary)


class TestCalculateIpcAdjustment:
    def test_hand_computed_two_years_at_five_percent(self):
        """Formula under test: base * ((1 + rate) ** years - 1).

        1000.00 at 5% for 2 years -> 1000 * (1.05**2 - 1) = 102.50.
        """
        result = calculate_ipc_adjustment(Decimal("1000.00"), years=2)
        assert result == Decimal("102.50")

    def test_zero_years_yields_zero(self):
        assert calculate_ipc_adjustment(Decimal("1000.00"), years=0) == Decimal("0")

    def test_result_is_quantized_to_cents(self):
        result = calculate_ipc_adjustment(Decimal("333.33"), years=3)
        assert result == result.quantize(Decimal("0.01"))


@pytest.mark.django_db
class TestTerminationService:
    def test_create_termination_requires_legalized_process(self, reviewer):
        beneficiary = _make_user()
        conv = Convocatory.objects.create(
            nombre="No legalizada", estado=Convocatory.Estado.EN_INSCRIPCION
        )
        process = LegalizationProcess.objects.create(
            beneficiary=beneficiary,
            convocatoria=conv,
            status=LegalizationProcess.Status.PENDIENTE,
        )
        with pytest.raises(ValueError, match="legalized"):
            TerminationService.create_termination(
                process, TerminationRequest.Cause.ABANDONO, reviewer
            )

    def test_create_termination_ok(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.ABANDONO, reviewer
        )
        assert termination.status == TerminationRequest.Status.PENDIENTE
        assert termination.requested_by == reviewer

    def test_approve_transitions_to_terminado(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.RETIRO_VOLUNTARIO, reviewer
        )
        result = TerminationService.approve_termination(termination.id, reviewer)
        assert result.status == TerminationRequest.Status.TERMINADO
        assert result.reviewed_by == reviewer
        assert result.reviewed_at is not None

    def test_approve_is_guarded_against_double_transition(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.RETIRO_VOLUNTARIO, reviewer
        )
        TerminationService.approve_termination(termination.id, reviewer)
        with pytest.raises(ValueError, match="Cannot approve"):
            TerminationService.approve_termination(termination.id, reviewer)

    def test_reject_transitions_to_rechazado(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.ABANDONO, reviewer
        )
        result = TerminationService.reject_termination(termination.id, reviewer)
        assert result.status == TerminationRequest.Status.RECHAZADO

    def test_fraud_cause_autocreates_sanction(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.INFORMACION_FALSA, reviewer
        )
        result = TerminationService.approve_termination(termination.id, reviewer)
        sanction = Sanction.objects.get(termination=result)
        assert sanction.status == Sanction.Status.PENDIENTE
        assert sanction.base_amount == Decimal("0")

    def test_non_trigger_cause_does_not_create_sanction(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.ABANDONO, reviewer
        )
        TerminationService.approve_termination(termination.id, reviewer)
        assert Sanction.objects.count() == 0

    def test_handle_death_condones_existing_sanction(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.MUERTE, reviewer
        )
        sanction = Sanction.objects.create(
            termination=termination,
            base_amount=Decimal("500.00"),
            total_amount=Decimal("500.00"),
        )
        TerminationService.handle_death_termination(termination.id, reviewer)
        termination.refresh_from_db()
        sanction.refresh_from_db()
        assert termination.status == TerminationRequest.Status.TERMINADO
        assert sanction.status == Sanction.Status.CONDONADA

    def test_handle_death_rejects_non_death_cause(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.ABANDONO, reviewer
        )
        with pytest.raises(ValueError, match="death"):
            TerminationService.handle_death_termination(termination.id, reviewer)


@pytest.mark.django_db
class TestSanctionService:
    @pytest.fixture
    def terminated_fraud_request(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.INFORMACION_FALSA, reviewer
        )
        return TerminationService.approve_termination(termination.id, reviewer)

    def test_create_sanction_applies_ipc_for_one_year(self, terminated_fraud_request):
        # Approving a fraud cause auto-creates a placeholder sanction
        # (OneToOne); drop it so we can create one with a known base.
        Sanction.objects.all().delete()
        sanction = SanctionService.create_sanction_from_termination(
            terminated_fraud_request, base_amount=Decimal("1000.00")
        )
        assert sanction.ipc_adjustment == Decimal("50.00")
        assert sanction.total_amount == Decimal("1050.00")

    def test_create_sanction_rejects_non_trigger_cause(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.ABANDONO, reviewer
        )
        TerminationService.approve_termination(termination.id, reviewer)
        with pytest.raises(ValueError, match="fraud"):
            SanctionService.create_sanction_from_termination(
                termination, base_amount=Decimal("100.00")
            )

    def test_submit_justification_starts_30_day_window(self, reviewer, terminated_fraud_request):
        sanction = Sanction.objects.get(termination=terminated_fraud_request)
        SanctionService.approve_sanction(sanction.id, reviewer)
        before = timezone.now()
        result = SanctionService.submit_justification(
            sanction.id,
            Sanction.Justification.ENFERMEDAD_GRAVE,
            "Certificación médica sintética",
        )
        after = timezone.now()
        assert result.status == Sanction.Status.EN_REVISION
        assert before + timedelta(days=29, hours=23) <= result.fecha_limite
        assert result.fecha_limite <= after + timedelta(days=30)

    def test_submit_justification_rejects_invalid_type(self, reviewer, terminated_fraud_request):
        sanction = Sanction.objects.get(termination=terminated_fraud_request)
        with pytest.raises(ValueError, match="Invalid justification"):
            SanctionService.submit_justification(sanction.id, "NO_EXISTE", "")

    def test_mark_as_expired_transitions_and_is_idempotent(
        self, reviewer, terminated_fraud_request
    ):
        sanction = Sanction.objects.get(termination=terminated_fraud_request)
        SanctionService.approve_sanction(sanction.id, reviewer)
        SanctionService.submit_justification(sanction.id, Sanction.Justification.ACCIDENTE, "")
        Sanction.objects.filter(id=sanction.id).update(
            fecha_limite=timezone.now() - timedelta(days=1)
        )
        SanctionService.mark_as_expired(sanction.id)
        sanction.refresh_from_db()
        assert sanction.status == Sanction.Status.VENCIDO
        # Idempotent: already-VENCIDO rows are left untouched.
        SanctionService.mark_as_expired(sanction.id)
        sanction.refresh_from_db()
        assert sanction.status == Sanction.Status.VENCIDO

    def test_condone_sanction(self, reviewer, terminated_fraud_request):
        sanction = Sanction.objects.get(termination=terminated_fraud_request)
        result = SanctionService.condone_sanction(sanction.id, reviewer)
        assert result.status == Sanction.Status.CONDONADA

    def test_confirm_payment_requires_approved_sanction(self, reviewer, terminated_fraud_request):
        sanction = Sanction.objects.get(termination=terminated_fraud_request)
        proof = SimpleUploadedFile("comprobante.pdf", b"%PDF-synthetic")
        with pytest.raises(ValueError, match="approved"):
            SanctionService.confirm_payment(sanction.id, proof, reviewer)

    def test_confirm_payment_ok(self, reviewer, terminated_fraud_request):
        sanction = Sanction.objects.get(termination=terminated_fraud_request)
        SanctionService.approve_sanction(sanction.id, reviewer)
        proof = SimpleUploadedFile("comprobante.pdf", b"%PDF-synthetic")
        result = SanctionService.confirm_payment(sanction.id, proof, reviewer)
        assert result.status == Sanction.Status.PAGADA
        assert result.paid_at is not None


@pytest.mark.django_db
class TestAuditTrail:
    """Every state change must reach the CAP-022 chain (design.md)."""

    def test_termination_lifecycle_writes_audit_events(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.INFORMACION_FALSA, reviewer
        )
        TerminationService.approve_termination(termination.id, reviewer)
        events = AuditEvent.objects.filter(module="condonation", entity="termination")
        actions = list(events.values_list("action", flat=True))
        assert "CREATE" in actions
        assert "UPDATE" in actions

    def test_sanction_flow_writes_audit_events(self, reviewer, legalized_process):
        termination = TerminationService.create_termination(
            legalized_process, TerminationRequest.Cause.SANCION_DISCIPLINARIA, reviewer
        )
        TerminationService.approve_termination(termination.id, reviewer)
        sanction = Sanction.objects.get(termination=termination)
        SanctionService.approve_sanction(sanction.id, reviewer)
        SanctionService.confirm_payment(
            sanction.id, SimpleUploadedFile("comprobante.pdf", b"%PDF-synthetic"), reviewer
        )
        assert AuditEvent.objects.filter(module="condonation", entity="sanction").count() >= 3
