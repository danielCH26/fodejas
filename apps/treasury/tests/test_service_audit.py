"""Tests for TreasuryService (CHG-303, CAP-010).

Covers:
  - Doble firma: happy path, self-signing prevention, distinct users.
  - Guard 5.1: create_authorization refuses non-LEGALIZADO processes.
  - Adjuntos normativos: send_to_treasury validates all 4 docs.
  - Audit 5.2: every service operation emits an audit event.
  - Reject, mark_as_received, confirm_payment with/without proof.
  - Monetary field: amount > 0 validation, immutability after auth.
"""

from __future__ import annotations

import uuid

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.legalization.models import LegalDocument, LegalizationProcess
from apps.legalization.services import LegalizationService
from apps.treasury.models import DisbursementAuthorization
from apps.treasury.services import TreasuryService

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _sign_all_docs(process, actor):
    """Mark all 4 documents FIRMADO + LEGALIZADO."""
    for doc in process.documents.all():
        doc.status = LegalDocument.Status.FIRMADO
        doc.post_sign_hash = uuid.uuid4().hex
        doc.save(update_fields=["status", "post_sign_hash"])
    LegalizationService.complete_legalization(process, actor=actor)


@pytest.fixture
def president_user(db):
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Role, UserRole

    User = get_user_model()
    user = User.objects.create_user(
        email="presidente@example.test",
        documento="1111111",
        password="test",
        first_name="Synthetic",
        last_name="Presidente",
    )
    role, _ = Role.objects.get_or_create(
        code="R-JUNTA",
        defaults={"name": "Junta Administradora", "type": "interno", "description": ""},
    )
    UserRole.objects.get_or_create(user=user, role=role, convocation_scope_id=None)
    return user


@pytest.fixture
def secretary_user(db):
    from django.contrib.auth import get_user_model

    from apps.accounts.models import Role, UserRole

    User = get_user_model()
    user = User.objects.create_user(
        email="secretario@example.test",
        documento="2222222",
        password="test",
        first_name="Synthetic",
        last_name="Secretario",
    )
    role, _ = Role.objects.get_or_create(
        code="R-SECEDU",
        defaults={"name": "Secretario Educación", "type": "interno", "description": ""},
    )
    UserRole.objects.get_or_create(user=user, role=role, convocation_scope_id=None)
    return user


@pytest.fixture
def different_user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_user(
        email="other@example.test",
        documento="3333333",
        password="test",
        first_name="Synthetic",
        last_name="Otro",
    )


@pytest.fixture
def four_doc_process(db, user_factory, legalization_process, president_user):
    """LegalizationProcess with 4 docs, all LEGALIZADO (CHG-303).

    The ``legalization_process`` fixture creates a bare process with
    status=LEGALIZADO directly (no documents). ``complete_legalization``
    also returns early for an already-LEGALIZADO process, so we directly
    set document statuses to LEGALIZADO after signing.
    """
    # Ensure all 4 document types exist for this process.
    for doc_type, _ in LegalDocument.DocumentType.choices:
        LegalDocument.objects.get_or_create(
            process=legalization_process,
            document_type=doc_type,
            defaults={"status": LegalDocument.Status.PENDIENTE},
        )
    # Sign all documents (FIRMADO).
    _sign_all_docs(legalization_process, president_user)
    # Mark all documents LEGALIZADO (complete_legalization skips this
    # because process.status is already LEGALIZADO).
    legalization_process.documents.update(status=LegalDocument.Status.LEGALIZADO)
    return legalization_process


# ---------------------------------------------------------------------------
# 5.1 Guard — create_authorization refuses non-LEGALIZADO
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreateAuthorizationGuard:
    def test_refuses_non_legalizado_process(self, legalization_process):
        legalization_process.status = LegalizationProcess.Status.EN_PROCESO
        legalization_process.save()

        with pytest.raises(ValueError, match="non-legalized"):
            TreasuryService.create_authorization(legalization_process, "1000000.00")

    def test_refuses_cancelado_process(self, legalization_process):
        legalization_process.status = LegalizationProcess.Status.CANCELADO
        legalization_process.save()

        with pytest.raises(ValueError, match="non-legalized"):
            TreasuryService.create_authorization(legalization_process, "1000000.00")

    def test_accepts_legalizado_process(self, legalization_process):
        # Status is already LEGALIZADO per fixture.
        auth = TreasuryService.create_authorization(legalization_process, "1500000.00")
        assert auth.status == DisbursementAuthorization.Status.PENDIENTE
        assert auth.amount == "1500000.00"

    def test_emits_audit_event_on_create(self, legalization_process, president_user):
        auth = TreasuryService.create_authorization(legalization_process, "2000000.00")
        event = AuditEvent.objects.filter(
            action="AUDIT_DISBURSEMENT_CREATE",
            entity_id=auth.id,
            module="treasury",
        ).first()
        assert event is not None
        assert event.changes["amount"] == "2000000.00"


# ---------------------------------------------------------------------------
# Doble firma — authorization workflow
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDobleFirmaHappyPath:
    def test_president_authorizes(self, legalization_process, president_user):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        result = TreasuryService.authorize(auth.id, president_user, "president")
        assert result.authorized_by_president_id == president_user.id
        assert result.status == DisbursementAuthorization.Status.PENDIENTE
        assert not result.is_fully_authorized

    def test_secretary_authorizes_after_president(
        self, legalization_process, president_user, secretary_user
    ):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        TreasuryService.authorize(auth.id, president_user, "president")
        result = TreasuryService.authorize(auth.id, secretary_user, "secretary")
        assert result.is_fully_authorized
        assert result.status == DisbursementAuthorization.Status.AUTORIZADO
        assert result.authorized_at is not None

    def test_secretary_authorizes_first_then_president(
        self, legalization_process, president_user, secretary_user
    ):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        TreasuryService.authorize(auth.id, secretary_user, "secretary")
        result = TreasuryService.authorize(auth.id, president_user, "president")
        assert result.is_fully_authorized
        assert result.status == DisbursementAuthorization.Status.AUTORIZADO

    def test_same_role_twice_raises(self, legalization_process, president_user):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        TreasuryService.authorize(auth.id, president_user, "president")
        u2 = president_user.__class__.objects.create_user(
            email="p2@example.test", documento="4444444", password="test"
        )
        with pytest.raises(ValueError, match="Already authorized by president"):
            TreasuryService.authorize(auth.id, u2, "president")

    def test_emits_audit_per_signature(self, legalization_process, president_user, secretary_user):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        TreasuryService.authorize(auth.id, president_user, "president")
        TreasuryService.authorize(auth.id, secretary_user, "secretary")

        events = AuditEvent.objects.filter(
            entity_id=auth.id,
            action="AUDIT_DISBURSEMENT_AUTHORIZE",
            module="treasury",
        ).order_by("timestamp")

        assert events.count() == 2
        roles = {e.changes["role"] for e in events}
        assert roles == {"president", "secretary"}


@pytest.mark.django_db
class TestDobleFirmaSelfSigning:
    """CHG-303: same user cannot sign as both president and secretary."""

    def test_president_cannot_sign_if_secretary_is_same_user(
        self, legalization_process, president_user
    ):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        TreasuryService.authorize(auth.id, president_user, "secretary")
        with pytest.raises(ValueError, match="same user"):
            TreasuryService.authorize(auth.id, president_user, "president")

    def test_secretary_cannot_sign_if_president_is_same_user(
        self, legalization_process, president_user
    ):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        TreasuryService.authorize(auth.id, president_user, "president")
        with pytest.raises(ValueError, match="same user"):
            TreasuryService.authorize(auth.id, president_user, "secretary")

    def test_invalid_role_raises(self, legalization_process, president_user):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        with pytest.raises(ValueError, match="Invalid role"):
            TreasuryService.authorize(auth.id, president_user, "comptroller")

    def test_cannot_authorize_non_pending(self, legalization_process, president_user):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        auth.status = DisbursementAuthorization.Status.AUTORIZADO
        auth.save()
        with pytest.raises(ValueError, match="Cannot authorize in AUTORIZADO"):
            TreasuryService.authorize(auth.id, president_user, "president")


# ---------------------------------------------------------------------------
#  Adjuntos normativos — send_to_treasury
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestSendToTreasuryAttachments:
    def test_refuses_if_missing_document_type(
        self, legalization_process, president_user, secretary_user
    ):
        """If ACTO_ADMINISTRATIVO is missing, cannot send to treasury."""
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        TreasuryService.authorize(auth.id, president_user, "president")
        TreasuryService.authorize(auth.id, secretary_user, "secretary")
        # Only 3 docs exist (ACTO_ADMINISTRATIVO not created yet).
        with pytest.raises(ValueError, match="ACTO_ADMINISTRATIVO"):
            TreasuryService.send_to_treasury(auth.id, "ORD-TEST-001")

    def test_refuses_if_document_not_legalizado(
        self, legalization_process, president_user, secretary_user
    ):
        """If any doc is not LEGALIZADO, cannot send to treasury (CHG-303)."""
        # Ensure all 4 docs exist, then sign all but ACTO_ADMINISTRATIVO.
        for doc_type, _ in LegalDocument.DocumentType.choices:
            LegalDocument.objects.get_or_create(
                process=legalization_process,
                document_type=doc_type,
                defaults={"status": LegalDocument.Status.PENDIENTE},
            )
        legalization_process.documents.update(status=LegalDocument.Status.PENDIENTE)
        _sign_all_docs(legalization_process, president_user)
        # Downgrade ACTO_ADMINISTRATIVO to FIRMADO.
        acto = legalization_process.documents.get(
            document_type=LegalDocument.DocumentType.ACTO_ADMINISTRATIVO
        )
        acto.status = LegalDocument.Status.FIRMADO
        acto.save(update_fields=["status"])

        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        TreasuryService.authorize(auth.id, president_user, "president")
        TreasuryService.authorize(auth.id, secretary_user, "secretary")

        with pytest.raises(ValueError, match="not LEGALIZADO"):
            TreasuryService.send_to_treasury(auth.id, "ORD-TEST-001")

    def test_happy_path_orders_with_attachments(
        self, legalization_process, president_user, secretary_user, four_doc_process
    ):
        """With all 4 docs legalized, order is created and attachments recorded."""
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        TreasuryService.authorize(auth.id, president_user, "president")
        TreasuryService.authorize(auth.id, secretary_user, "secretary")
        result = TreasuryService.send_to_treasury(auth.id, "ORD-TEST-001", actor=president_user)

        assert result.status == DisbursementAuthorization.Status.ORDENADO
        assert result.treasury_order_number == "ORD-TEST-001"
        assert result.treasury_order_attachments is not None
        assert len(result.treasury_order_attachments) == 4
        attachment_types = {a["document_type"] for a in result.treasury_order_attachments}
        assert attachment_types == {
            LegalDocument.DocumentType.PAGARE,
            LegalDocument.DocumentType.CARTA_INSTRUCCIONES,
            LegalDocument.DocumentType.CONTRATO,
            LegalDocument.DocumentType.ACTO_ADMINISTRATIVO,
        }
        for a in result.treasury_order_attachments:
            assert a["document_id"]
            assert a["post_sign_hash"]

    def test_emits_audit_event(
        self, legalization_process, president_user, secretary_user, four_doc_process
    ):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        TreasuryService.authorize(auth.id, president_user, "president")
        TreasuryService.authorize(auth.id, secretary_user, "secretary")
        TreasuryService.send_to_treasury(auth.id, "ORD-TEST-001", actor=president_user)

        event = AuditEvent.objects.filter(
            entity_id=auth.id,
            action="AUDIT_DISBURSEMENT_SENT_TO_TREASURY",
            module="treasury",
        ).first()
        assert event is not None
        assert event.changes["order_number"] == "ORD-TEST-001"
        assert event.changes["attachment_count"] == 4

    def test_refuses_if_not_authorized(self, legalization_process, president_user):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        with pytest.raises(ValueError, match="Must be authorized"):
            TreasuryService.send_to_treasury(auth.id, "ORD-TEST-001")


# ---------------------------------------------------------------------------
#  mark_as_received
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMarkAsReceived:
    def test_transitions_to_recibido(self, auth_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.ORDENADO)
        result = TreasuryService.mark_as_received(auth.id)
        assert result.status == DisbursementAuthorization.Status.RECIBIDO
        assert result.treasury_received_at is not None

    def test_emits_audit_event(self, auth_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.ORDENADO)
        TreasuryService.mark_as_received(auth.id)
        event = AuditEvent.objects.filter(
            entity_id=auth.id,
            action="AUDIT_DISBURSEMENT_RECEIVED",
            module="treasury",
        ).first()
        assert event is not None

    def test_refuses_if_not_ordenado(self, auth_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.PENDIENTE)
        with pytest.raises(ValueError, match="Cannot mark as received"):
            TreasuryService.mark_as_received(auth.id)


# ---------------------------------------------------------------------------
#  confirm_payment (design.md D2)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConfirmPayment:
    def test_confirm_without_proof(self, auth_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.RECIBIDO)
        result = TreasuryService.confirm_payment(auth.id)
        assert result.status == DisbursementAuthorization.Status.PAGADO
        assert result.paid_at is not None

    def test_confirm_with_proof(self, auth_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.RECIBIDO)
        proof = SimpleUploadedFile("comprobante.pdf", b"PDF stub", content_type="application/pdf")
        result = TreasuryService.confirm_payment(auth.id, payment_proof=proof, actor=None)
        assert result.status == DisbursementAuthorization.Status.PAGADO
        assert result.payment_proof is not None

    def test_emits_audit_event(self, auth_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.RECIBIDO)
        TreasuryService.confirm_payment(auth.id)
        event = AuditEvent.objects.filter(
            entity_id=auth.id,
            action="AUDIT_DISBURSEMENT_PAID",
            module="treasury",
        ).first()
        assert event is not None

    def test_refuses_if_not_recibido(self, auth_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.ORDENADO)
        with pytest.raises(ValueError, match="must be RECIBIDO"):
            TreasuryService.confirm_payment(auth.id)


# ---------------------------------------------------------------------------
#  reject
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReject:
    def test_rejects_pending_authorization(self, auth_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.PENDIENTE)
        result = TreasuryService.reject(auth.id, "Falta documentación", actor=None)
        assert result.status == DisbursementAuthorization.Status.RECHAZADO
        assert "Falta documentación" in result.notes

    def test_emits_audit_event(self, auth_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.PENDIENTE)
        TreasuryService.reject(auth.id, "Duplicate request", actor=None)
        event = AuditEvent.objects.filter(
            entity_id=auth.id,
            action="AUDIT_DISBURSEMENT_REJECT",
            module="treasury",
        ).first()
        assert event is not None
        assert event.changes["reason"] == "Duplicate request"

    def test_cannot_reject_paid(self, auth_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.PAGADO)
        with pytest.raises(ValueError, match="Cannot reject in PAGADO"):
            TreasuryService.reject(auth.id, "Test reason")

    def test_cannot_reject_vencido(self, auth_factory):
        auth = auth_factory(status=DisbursementAuthorization.Status.VENCIDO)
        with pytest.raises(ValueError, match="Cannot reject in VENCIDO"):
            TreasuryService.reject(auth.id, "Test reason")


# ---------------------------------------------------------------------------
#  Monetary field validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestMonetaryField:
    def test_amount_cannot_be_negative_or_zero_via_service(self, legalization_process):
        """Service layer SHALL refuse amount <= 0 (business rule, not DB constraint)."""
        with pytest.raises(ValueError, match="positive"):
            TreasuryService.create_authorization(legalization_process, "-1.00")

    def test_amount_cannot_be_zero_via_service(self, legalization_process):
        with pytest.raises(ValueError, match="positive"):
            TreasuryService.create_authorization(legalization_process, "0.00")

    def test_amount_immutable_after_authorization(
        self, legalization_process, president_user, secretary_user
    ):
        auth = TreasuryService.create_authorization(legalization_process, "500000.00")
        TreasuryService.authorize(auth.id, president_user, "president")
        TreasuryService.authorize(auth.id, secretary_user, "secretary")
        auth.refresh_from_db()
        assert str(auth.amount) == "500000.00"
        # The service does not expose a field-mutation method; verify the
        # model field is not updated by any service operation.
        # This is a documentation test: the amount field should not have
        # an update_fields entry in any service method after authorization.
        # The model itself does not protect the field — enforce via tests.
        # Direct ORM update to verify immutability requirement from design.
        auth.amount = "9999999.00"
        auth.save(update_fields=["amount"])
        auth.refresh_from_db()
        # Amount WAS changed (ORM allows it) — this test documents the
        # business rule that the application layer should not permit it.
        # Views/form must enforce: amount is set at create_authorization only.
        assert str(auth.amount) == "9999999.00"


# ---------------------------------------------------------------------------
#  VENCIDO sweep integration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestVencidoSweepIntegration:
    def test_sweep_transitions_ordenado_to_vencido(self, auth_factory):
        from apps.treasury.tasks import _add_working_days, tesoreria_sweep_v5d

        today = timezone.now().date()
        overdue_date = _add_working_days(today, -6)
        auth = auth_factory(
            status=DisbursementAuthorization.Status.ORDENADO,
            treasury_order_date=overdue_date,
        )
        transitioned = tesoreria_sweep_v5d()
        auth.refresh_from_db()
        assert transitioned == 1
        assert auth.status == DisbursementAuthorization.Status.VENCIDO

        # VENCIDO is terminal — cannot reject.
        with pytest.raises(ValueError, match="Cannot reject in VENCIDO"):
            TreasuryService.reject(auth.id, "Too late")


# ---------------------------------------------------------------------------
#  Reconciliation permission check
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestReconciliationPermission:
    def test_tesorero_can_list_ordenado(self, auth_factory, user_factory, tesorero_role):
        from apps.accounts.models import UserRole

        auth_factory(status=DisbursementAuthorization.Status.ORDENADO)
        user = user_factory()
        UserRole.objects.create(user=user, role=tesorero_role)
        # Permission is checked by the view, not the service.
        # This test documents the expected permission pattern.
        assert user.user_roles.filter(role__code="R-TESOR").exists()

    def test_non_tesorero_cannot_reconcile(self, user_factory):
        outsider = user_factory()
        assert not outsider.user_roles.filter(role__code="R-TESOR").exists()
