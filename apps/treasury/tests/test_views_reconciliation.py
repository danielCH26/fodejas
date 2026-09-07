"""Integration tests for the treasury reconciliation view (CHG-802)."""
from __future__ import annotations

import io

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.treasury.models import DisbursementAuthorization


@pytest.fixture
def tesorero_user_with_role(user_factory, tesorero_role):
    from apps.accounts.models import UserRole

    user = user_factory()
    UserRole.objects.create(user=user, role=tesorero_role)
    return user


@pytest.fixture
def authorized_user(user_factory):
    return user_factory()


@pytest.mark.django_db(transaction=True)
class TestTreasuryReconciliationView:
    """CAP-010: R-TESORERO can list and confirm ordered payments."""

    def test_get_lists_ordenado_rows(
        self, auth_factory, tesorero_user_with_role
    ):
        auth = auth_factory(
            status=DisbursementAuthorization.Status.ORDENADO,
            treasury_order_date=timezone.now().date(),
            treasury_order_number="ORD-001",
        )
        client = Client()
        client.force_login(tesorero_user_with_role)
        resp = client.get(reverse("treasury:reconciliation"))
        assert resp.status_code == 200
        assert auth.id in [a.id for a in resp.context["authorizations"]]

    def test_post_with_payment_proof_marks_paid_and_audits(
        self, auth_factory, tesorero_user_with_role, authorized_user
    ):
        auth = auth_factory(
            status=DisbursementAuthorization.Status.ORDENADO,
            treasury_order_date=timezone.now().date(),
            treasury_order_number="ORD-002",
        )
        client = Client()
        client.force_login(tesorero_user_with_role)

        # Tiny in-memory "PDF" stub.
        proof = io.BytesIO(b"%PDF-1.4 stub content")
        proof.name = "comprobante.pdf"

        resp = client.post(
            reverse("treasury:reconciliation"),
            data={
                "auth_id": str(auth.id),
                "payment_proof": proof,
            },
            format="multipart",
        )
        assert resp.status_code in (200, 302)

        auth.refresh_from_db()
        assert auth.status == DisbursementAuthorization.Status.PAGADO
        assert auth.paid_at is not None

        audit = (
            AuditEvent.objects.filter(
                entity="DisbursementAuthorization",
                entity_id=auth.id,
                action="PAYMENT_CONFIRMED",
            )
            .order_by("-timestamp")
            .first()
        )
        assert audit is not None
        assert audit.actor_id == tesorero_user_with_role.id

    def test_non_tesorero_user_is_forbidden(
        self, auth_factory, user_factory
    ):
        auth_factory(
            status=DisbursementAuthorization.Status.ORDENADO,
            treasury_order_date=timezone.now().date(),
        )
        outsider = user_factory()
        client = Client()
        client.force_login(outsider)
        resp = client.get(reverse("treasury:reconciliation"))
        assert resp.status_code == 403
