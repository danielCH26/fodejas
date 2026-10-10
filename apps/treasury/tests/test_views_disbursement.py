"""View tests for disbursement authorization UI (CHG-303, CAP-010).

Tests:
  - List view: R-JUNTA sees all PENDIENTE+AUTORIZADO; other role → 403
  - Detail view: authorization context (dual-signature state, attachments)
  - Authorize POST: happy path (two signatures complete authorization),
    self-sign rejection, duplicate-role rejection
  - URL routing: list, detail, authorize endpoints resolve correctly
"""

from __future__ import annotations

import uuid

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import CustomUser, Role, UserRole
from apps.legalization.models import LegalDocument, LegalizationProcess
from apps.treasury.models import DisbursementAuthorization
from apps.treasury.services import TreasuryService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(email=None, role_codes=("R-JUNTA",)):
    email = email or f"{uuid.uuid4().hex}@example.test"
    user = CustomUser.objects.create_user(
        email=email,
        documento=uuid.uuid4().hex[:12],
        password="test-password-not-real",
        first_name="Synthetic",
        last_name="Test",
    )
    for code in role_codes:
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={"name": code, "type": "interno", "description": code},
        )
        UserRole.objects.get_or_create(user=user, role=role, convocation_scope_id=None)
    return user


def _session_client(user):
    client = Client()
    client.force_login(user)
    return client


def _auth_factory(status="PENDIENTE", **extra):
    def _make(legalization_process, amount="1000000.00", **kw):
        return DisbursementAuthorization.objects.create(
            legalization_process=legalization_process,
            amount=amount,
            status=status,
            **kw,
        )

    return _make


@pytest.fixture
def four_doc_process(db, user_factory):
    """LegalizationProcess with all 4 docs LEGALIZADO."""
    beneficiary = user_factory(email="benef@example.test")
    from apps.convocatories.models import Convocatory

    conv = Convocatory.objects.create(
        nombre="Convocatoria Sintética",
        codigo=f"syn-{uuid.uuid4().hex[:8].upper()}",
        tipo="cerrada",
        periodo="2099-1",
        monto_semestre_smlmv=5,
        duracion_maxima_semestres=10,
        cupo_total=10,
        estado=Convocatory.Estado.DEFINITIVA,
    )
    process = LegalizationProcess.objects.create(
        beneficiary=beneficiary,
        convocatoria=conv,
        status=LegalizationProcess.Status.LEGALIZADO,
    )
    for doc_type, _ in LegalDocument.DocumentType.choices:
        LegalDocument.objects.create(
            process=process,
            document_type=doc_type,
            status=LegalDocument.Status.LEGALIZADO,
        )
    return process


# ---------------------------------------------------------------------------
# URL tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDisbursementURLs:
    def test_list_url_resolves(self):
        assert reverse("treasury:disbursement_list") == "/treasury/"

    def test_detail_url_resolves(self, four_doc_process):
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        assert (
            reverse("treasury:disbursement_detail", kwargs={"pk": auth.pk})
            == f"/treasury/{auth.pk}/"
        )

    def test_authorize_url_resolves(self, four_doc_process):
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        assert (
            reverse("treasury:authorize", kwargs={"pk": auth.pk})
            == f"/treasury/{auth.pk}/autorizar/"
        )


# ---------------------------------------------------------------------------
# List view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDisbursementListView:
    def test_junta_sees_list(self, four_doc_process):
        """R-JUNTA gets 200 on the authorization list."""
        junta = _make_user(role_codes=["R-JUNTA"])
        DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        client = _session_client(junta)
        resp = client.get(reverse("treasury:disbursement_list"))
        assert resp.status_code == 200

    def test_coordinador_sees_list(self, four_doc_process):
        """R-COORDINADOR (secretary) gets 200 on the authorization list."""
        coord = _make_user(role_codes=["R-COORDINADOR"])
        DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        client = _session_client(coord)
        resp = client.get(reverse("treasury:disbursement_list"))
        assert resp.status_code == 200

    def test_non_authorized_role_forbidden(self, four_doc_process):
        """User without R-JUNTA/R-COORDINADOR gets 403."""
        outsider = _make_user(role_codes=["R-ASPIRANTE"])
        DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        client = _session_client(outsider)
        resp = client.get(reverse("treasury:disbursement_list"))
        assert resp.status_code == 403

    def test_staff_sees_list(self, four_doc_process):
        """Staff user sees the list even without R-JUNTA/R-COORDINADOR."""
        staff = _make_user(role_codes=["R-ASPIRANTE"])
        staff.is_staff = True
        staff.save(update_fields=["is_staff"])
        DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        client = _session_client(staff)
        resp = client.get(reverse("treasury:disbursement_list"))
        assert resp.status_code == 200

    def test_list_shows_pendiente_and_autorizado(self, four_doc_process):
        """List includes PENDIENTE and AUTORIZADO authorizations."""
        junta = _make_user(role_codes=["R-JUNTA"])
        p1 = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="100000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        p2 = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="200000.00",
            status=DisbursementAuthorization.Status.AUTORIZADO,
        )
        DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="999999.00",
            status=DisbursementAuthorization.Status.PAGADO,  # excluded
        )
        client = _session_client(junta)
        resp = client.get(reverse("treasury:disbursement_list"))
        assert resp.status_code == 200
        ids = [a.id for a in resp.context["authorizations"]]
        assert p1.id in ids
        assert p2.id in ids
        # PAGADO excluded


# ---------------------------------------------------------------------------
# Detail view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDisbursementDetailView:
    def test_junta_can_access_detail(self, four_doc_process):
        """R-JUNTA can view any authorization detail."""
        junta = _make_user(role_codes=["R-JUNTA"])
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        client = _session_client(junta)
        resp = client.get(reverse("treasury:disbursement_detail", kwargs={"pk": auth.pk}))
        assert resp.status_code == 200
        assert resp.context["authorization"] == auth

    def test_detail_context_has_legalization_process(self, four_doc_process):
        """Detail context includes the related legalization process."""
        junta = _make_user(role_codes=["R-JUNTA"])
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        client = _session_client(junta)
        resp = client.get(reverse("treasury:disbursement_detail", kwargs={"pk": auth.pk}))
        assert resp.context["process"] == four_doc_process

    def test_detail_context_shows_partial_signature_state(self, four_doc_process):
        """When only president has signed, context shows missing secretary."""
        president = _make_user(role_codes=["R-JUNTA"])
        secretary = _make_user(email="sec@example.test", role_codes=["R-COORDINADOR"])
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        # President signs first.
        TreasuryService.authorize(auth.id, president, role="president")

        client = _session_client(secretary)
        resp = client.get(reverse("treasury:disbursement_detail", kwargs={"pk": auth.pk}))
        assert resp.status_code == 200
        assert resp.context["can_sign"] is True  # Secretary can still sign
        assert resp.context["missing_role"] == "secretary"

    def test_detail_context_shows_fully_authorized(self, four_doc_process):
        """When both signed, can_sign=False (already complete)."""
        president = _make_user(role_codes=["R-JUNTA"])
        secretary = _make_user(email="sec2@example.test", role_codes=["R-COORDINADOR"])
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        TreasuryService.authorize(auth.id, president, role="president")
        TreasuryService.authorize(auth.id, secretary, role="secretary")

        junta = _make_user(role_codes=["R-JUNTA"])
        client = _session_client(junta)
        resp = client.get(reverse("treasury:disbursement_detail", kwargs={"pk": auth.pk}))
        assert resp.context["can_sign"] is False
        assert resp.context["authorization"].status == DisbursementAuthorization.Status.AUTORIZADO

    def test_detail_context_has_attachment_types(self, four_doc_process):
        """Detail shows the 4 required normative attachment types."""
        junta = _make_user(role_codes=["R-JUNTA"])
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        client = _session_client(junta)
        resp = client.get(reverse("treasury:disbursement_detail", kwargs={"pk": auth.pk}))
        assert "required_attachment_types" in resp.context
        assert len(resp.context["required_attachment_types"]) == 4


# ---------------------------------------------------------------------------
# Authorize HTMX view
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestAuthorizeView:
    def test_president_signs_successfully(self, four_doc_process):
        """First signature (president) transitions auth to PENDIENTE with 1 sig."""
        president = _make_user(role_codes=["R-JUNTA"])
        _make_user(email="sec3@example.test", role_codes=["R-COORDINADOR"])
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        client = _session_client(president)
        resp = client.post(
            reverse("treasury:authorize", kwargs={"pk": auth.pk}),
            data={"role": "president"},
        )
        # HTMX: 200 with swap header
        assert resp.status_code == 200
        assert "HX-Reswap" in resp.headers
        auth.refresh_from_db()
        assert auth.authorized_by_president == president
        assert auth.status == DisbursementAuthorization.Status.PENDIENTE

    def test_second_signature_completes_authorization(self, four_doc_process):
        """Second signature (secretary) transitions auth to AUTORIZADO."""
        president = _make_user(role_codes=["R-JUNTA"])
        secretary = _make_user(email="sec4@example.test", role_codes=["R-COORDINADOR"])
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        # President signs first.
        TreasuryService.authorize(auth.id, president, role="president")
        # Secretary signs second.
        client = _session_client(secretary)
        resp = client.post(
            reverse("treasury:authorize", kwargs={"pk": auth.pk}),
            data={"role": "secretary"},
        )
        assert resp.status_code == 200
        auth.refresh_from_db()
        assert auth.status == DisbursementAuthorization.Status.AUTORIZADO
        assert auth.authorized_by_secretary == secretary
        assert auth.authorized_at is not None

    def test_self_sign_rejected(self, four_doc_process):
        """Same user cannot be both president and secretary."""
        junta = _make_user(role_codes=["R-JUNTA", "R-COORDINADOR"])
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        # Sign as president.
        TreasuryService.authorize(auth.id, junta, role="president")
        # Try to sign as secretary (same user) → 400
        client = _session_client(junta)
        resp = client.post(
            reverse("treasury:authorize", kwargs={"pk": auth.pk}),
            data={"role": "secretary"},
        )
        assert resp.status_code == 400
        assert (
            "mismo usuario" in resp.content.decode().lower()
            or "same user" in resp.content.decode().lower()
        )

    def test_duplicate_role_rejected(self, four_doc_process):
        """User cannot sign the same role twice."""
        president = _make_user(role_codes=["R-JUNTA"])
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        # First sign.
        TreasuryService.authorize(auth.id, president, role="president")
        # Second sign as same role → 400
        client = _session_client(president)
        resp = client.post(
            reverse("treasury:authorize", kwargs={"pk": auth.pk}),
            data={"role": "president"},
        )
        assert resp.status_code == 400
        assert "already" in resp.content.decode().lower() or "ya" in resp.content.decode().lower()

    def test_non_authorized_role_forbidden(self, four_doc_process):
        """User without R-JUNTA/R-COORDINADOR cannot access authorize view."""
        outsider = _make_user(role_codes=["R-ASPIRANTE"])
        auth = DisbursementAuthorization.objects.create(
            legalization_process=four_doc_process,
            amount="500000.00",
            status=DisbursementAuthorization.Status.PENDIENTE,
        )
        client = _session_client(outsider)
        resp = client.post(
            reverse("treasury:authorize", kwargs={"pk": auth.pk}),
            data={"role": "president"},
        )
        assert resp.status_code == 403
