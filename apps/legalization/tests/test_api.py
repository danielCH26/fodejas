"""Tests for legalization API endpoints (CHG-301, CAP-029)."""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import CustomUser, Role, UserRole
from apps.audit.models import AuditEvent
from apps.convocatories.models import Convocatory
from apps.legalization.models import LegalDocument, LegalizationProcess

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_pdf(name="doc.pdf") -> SimpleUploadedFile:
    content = b"%PDF-1.4 fake content for tests " + name.encode()
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def _make_user(email, role_codes=("R-ASPIRANTE",)):
    import uuid

    user = CustomUser.objects.create(
        email=email,
        documento=uuid.uuid4().hex[:20],
        telefono="3000000000",
    )
    for code in role_codes:
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={"name": code, "type": "interno", "description": code},
        )
        UserRole.objects.get_or_create(user=user, role=role, convocation_scope_id=None)
    return user


def _make_convocatoria():
    return Convocatory.objects.create(
        nombre="Convocatoria Test",
        codigo="CT-2026-001",
        tipo="cerrada",
        periodo="2026-1",
        monto_semestre_smlmv=5,
        duracion_maxima_semestres=10,
        cupo_total=10,
        estado=Convocatory.Estado.DEFINITIVA,
    )


def _make_process(convocatoria, beneficiary):
    process = LegalizationProcess.objects.create(
        beneficiary=beneficiary,
        convocatoria=convocatoria,
        status=LegalizationProcess.Status.PENDIENTE,
    )
    for doc_type, _ in LegalDocument.DocumentType.choices:
        LegalDocument.objects.create(
            process=process,
            document_type=doc_type,
            status=LegalDocument.Status.PENDIENTE,
        )
    return process


def _api_client(user, force=False):
    """Return an authenticated APIClient for the given user.

    Args:
        user: CustomUser instance.
        force: If True, use force_authenticate (no JWT needed).
               Useful when JWT token creation has side-effects in test context.
    """

    if force:
        client = APIClient()
        client.force_authenticate(user=user)
        return client

    client = APIClient()
    refresh = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client


# ---------------------------------------------------------------------------
# Document sign endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestSignEndpoint:
    """POST /api/legalization/documents/<pk>/sign/"""

    def setup_method(self):
        self.aspirante = _make_user("asp@example.com", ["R-ASPIRANTE"])
        self.admin = _make_user("admin@example.com", ["R-ADMIN"])
        self.junta = _make_user("junta@example.com", ["R-JUNTA"])
        self.conv = _make_convocatoria()
        self.process = _make_process(self.conv, self.aspirante)
        # Explicitly get the PAGARE document (first() order is not guaranteed).
        self.doc = self.process.documents.get(document_type=LegalDocument.DocumentType.PAGARE)
        self.doc.pdf = _make_pdf("pagare.pdf")
        self.doc.save()
        self.url = f"/api/legalization/documents/{self.doc.id}/sign/"

    def test_sign_returns_200_with_signature_result(self):
        """A valid sign request returns 200 and hashes."""
        client = _api_client(self.aspirante)
        response = client.post(self.url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(self.doc.id)
        assert data["pre_sign_hash"]
        assert data["post_sign_hash"]
        assert data["provider"] in ("mock", "local")
        assert data["signed_at"] is not None

    def test_sign_persists_hashes_on_document(self):
        """After signing, the document has persisted hashes."""
        client = _api_client(self.aspirante)
        client.post(self.url)
        self.doc.refresh_from_db()
        assert bool(self.doc.pre_sign_hash)
        assert bool(self.doc.post_sign_hash)
        assert self.doc.status == LegalDocument.Status.FIRMADO

    def test_sign_idempotent_second_call_returns_same_result(self):
        """Re-signing an already-signed document returns the same hashes."""
        client = _api_client(self.aspirante)

        # First sign.
        r1 = client.post(self.url)
        assert r1.status_code == status.HTTP_200_OK
        first_post_hash = r1.json()["post_sign_hash"]
        first_signed_at = r1.json()["signed_at"]

        # Second call — idempotent, same hashes and timestamp.
        r2 = client.post(self.url)
        assert r2.status_code == status.HTTP_200_OK
        assert r2.json()["post_sign_hash"] == first_post_hash
        assert r2.json()["signed_at"] == first_signed_at

    def test_sign_creates_audit_event(self):
        """A sign request creates exactly one ELECTRONIC_SIGNATURE audit event."""
        client = _api_client(self.aspirante)
        client.post(self.url)
        self.doc.refresh_from_db()
        events = AuditEvent.objects.filter(action="ELECTRONIC_SIGNATURE")
        assert events.count() == 1
        assert events.first().changes["pre_sign_hash"] == self.doc.pre_sign_hash

    def test_sign_fails_without_auth(self):
        """An unauthenticated request returns 401."""
        client = APIClient()
        response = client.post(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_sign_fails_for_wrong_user(self):
        """A different Aspirante cannot sign this document (404 — filtered out)."""
        other_user = _make_user("other@example.com")
        client = _api_client(other_user)
        response = client.post(self.url)
        # The queryset filters by beneficiary, so this Aspirante sees nothing → 404.
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_sign_fails_without_pdf(self):
        """A document without a PDF returns 400."""
        self.doc.pdf = None
        self.doc.save()
        client = _api_client(self.aspirante)
        response = client.post(self.url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "no tiene PDF" in response.json()["detail"]

    def test_admin_can_sign_any_document(self):
        """R-ADMIN can sign any document regardless of beneficiary."""
        # Use force_authenticate to avoid JWT side-effects in test context.
        client = _api_client(self.admin, force=True)
        response = client.post(self.url)
        if response.status_code != status.HTTP_200_OK:
            print(f"Admin sign failed: {response.status_code} {response.json()}")
        assert response.status_code == status.HTTP_200_OK

    def test_junta_can_sign_any_document(self):
        """R-JUNTA can sign any document regardless of beneficiary."""
        client = _api_client(self.junta, force=True)
        response = client.post(self.url)
        assert response.status_code == status.HTTP_200_OK

    def test_sign_fails_for_already_signed_document(self):
        """A document already in FIRMADO status returns 200 (idempotent)."""
        self.doc.status = LegalDocument.Status.FIRMADO
        self.doc.pre_sign_hash = "a" * 64
        self.doc.post_sign_hash = "b" * 64
        self.doc.save()
        client = _api_client(self.aspirante)
        response = client.post(self.url)
        # Idempotent — returns current state, no error.
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["post_sign_hash"] == "b" * 64


# ---------------------------------------------------------------------------
# Document verify endpoint
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestVerifyEndpoint:
    """GET /api/legalization/documents/<pk>/verify/"""

    def setup_method(self):
        self.admin = _make_user("admin@example.com", ["R-ADMIN"])
        conv = _make_convocatoria()
        process = LegalizationProcess.objects.create(
            beneficiary=self.admin,
            convocatoria=conv,
        )
        # Create a single document for the process.
        doc = LegalDocument.objects.create(
            process=process,
            document_type=LegalDocument.DocumentType.PAGARE,
            status=LegalDocument.Status.PENDIENTE,
        )
        doc.pdf = _make_pdf("pagare.pdf")
        doc.save()
        self.doc = doc
        self.url = f"/api/legalization/documents/{self.doc.id}/verify/"

    def test_verify_returns_200_and_is_integral_true(self):
        """After signing, verify returns is_integral=True."""
        # Sign the document first.
        from apps.legalization.services import sign_legal_document

        sign_legal_document(self.doc, actor=self.admin)
        client = _api_client(self.admin)
        response = client.get(self.url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_integral"] is True
        assert data["pre_sign_hash"] == self.doc.pre_sign_hash

    def test_verify_fails_if_not_signed(self):
        """A document without a pre_sign_hash returns 400."""
        client = _api_client(self.admin)
        response = client.get(self.url)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "no ha sido firmado" in response.json()["detail"]

    def test_verify_fails_without_auth(self):
        """An unauthenticated request returns 401."""
        client = APIClient()
        response = client.get(self.url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# End-to-end flow: process → request → sign → verify → audit
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestE2ESignatureFlow:
    """Full flow: create process → sign via API → verify hash chain → audit."""

    def test_e2e_create_sign_verify_audit_flow(self):
        """Process → sign → verify → audit event recorded, hash chain intact."""
        # 1. Create user and process.
        user = _make_user("beneficiario@example.com", ["R-ASPIRANTE"])
        conv = _make_convocatoria()
        process = _make_process(conv, user)

        # 2. Get the promissory note document.
        doc = process.documents.get(document_type=LegalDocument.DocumentType.PAGARE)
        doc.pdf = _make_pdf("pagare-e2e.pdf")
        doc.save()

        # 3. Sign via API.
        client = _api_client(user)
        sign_resp = client.post(f"/api/legalization/documents/{doc.id}/sign/")
        assert sign_resp.status_code == status.HTTP_200_OK
        sign_data = sign_resp.json()
        assert sign_data["status"] == "FIRMADO"
        assert sign_data["pre_sign_hash"]
        assert sign_data["post_sign_hash"]
        assert sign_data["signed_at"]

        # 4. Verify hash chain via API.
        verify_resp = client.get(f"/api/legalization/documents/{doc.id}/verify/")
        assert verify_resp.status_code == status.HTTP_200_OK
        verify_data = verify_resp.json()
        assert verify_data["is_integral"] is True
        assert verify_data["pre_sign_hash"] == sign_data["pre_sign_hash"]

        # 5. Refresh doc from DB and verify state.
        doc.refresh_from_db()
        assert doc.status == LegalDocument.Status.FIRMADO
        assert doc.pre_sign_hash == sign_data["pre_sign_hash"]

        # 6. Audit event recorded.
        events = AuditEvent.objects.filter(
            action="ELECTRONIC_SIGNATURE",
            entity=f"legal_{doc.document_type.lower()}",
            entity_id=doc.id,
        )
        assert events.count() == 1
        audit = events.first()
        assert audit.changes["pre_sign_hash"] == doc.pre_sign_hash
        assert audit.changes["post_sign_hash"] == doc.post_sign_hash

        # 7. Idempotency: re-signing is a no-op.
        doc2_resp = client.post(f"/api/legalization/documents/{doc.id}/sign/")
        assert doc2_resp.status_code == status.HTTP_200_OK
        assert doc2_resp.json()["post_sign_hash"] == sign_data["post_sign_hash"]
        # No second audit event.
        assert (
            AuditEvent.objects.filter(action="ELECTRONIC_SIGNATURE", entity_id=doc.id).count() == 1
        )
