"""Tests for apps.legalization.signer and sign_legal_document (CHG-301)."""
from __future__ import annotations

import hashlib
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from apps.accounts.models import CustomUser, Role, UserRole
from apps.applications.models import Solicitud
from apps.audit.models import AuditEvent
from apps.convocatories.models import Convocatory
from apps.legalization.models import LegalDocument, LegalizationProcess
from apps.legalization.services import sign_legal_document
from apps.legalization.signer import (
    LocalSigner,
    MockSigner,
    SignerFactory,
    sign_document,
    verify_document,
)


def _make_pdf(name="doc.pdf") -> SimpleUploadedFile:
    content = b"%PDF-1.4 fake content for tests " + name.encode()
    return SimpleUploadedFile(name, content, content_type="application/pdf")


def _make_user(role_codes=("R-JUNTA",)):
    import uuid as uuidlib

    user = CustomUser.objects.create(
        email=f"{uuidlib.uuid4().hex}@example.com",
        documento=uuidlib.uuid4().hex[:20],
        telefono="3000000000",
    )
    for code in role_codes:
        role, _ = Role.objects.get_or_create(
            code=code,
            defaults={"name": code, "type": "interno", "description": code},
        )
        UserRole.objects.get_or_create(
            user=user, role=role, convocation_scope_id=None
        )
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


def _make_solicitud(convocatoria, aspirante):
    import uuid as uuidlib

    return Solicitud.objects.create(
        convocatoria=convocatoria,
        aspirante=aspirante,
        radicado=f"RAD-{uuidlib.uuid4().hex[:8]}",
        estado=Solicitud.Estado.RADICADA,
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


# ---------------------------------------------------------------------------
# Signer unit tests
# ---------------------------------------------------------------------------


class TestSignerAlgorithms:
    def test_mock_signer_is_deterministic(self):
        signer = MockSigner()
        a = signer.sign(b"hello world")
        b = signer.sign(b"hello world")
        assert a.pre_sign_hash == b.pre_sign_hash
        # post_sign_hash is also deterministic now (fixed-epoch blob —
        # design.md D1 / CHG-301 proposal §1 for reproducible tests).
        assert a.post_sign_hash == b.post_sign_hash

    def test_local_signer_is_deterministic(self):
        signer = LocalSigner()
        a = signer.sign(b"hello world")
        b = signer.sign(b"hello world")
        assert a.pre_sign_hash == b.pre_sign_hash
        assert a.post_sign_hash == b.post_sign_hash

    def test_pre_hash_matches_sha256(self):
        data = b"some document content"
        for signer in (MockSigner(), LocalSigner()):
            result = signer.sign(data)
            assert result.pre_sign_hash == hashlib.sha256(data).hexdigest()

    def test_post_hash_differs_from_pre_hash(self):
        signer = MockSigner()
        result = signer.sign(b"some content")
        assert result.post_sign_hash != result.pre_sign_hash

    def test_mock_metadata_marks_development(self):
        result = MockSigner().sign(b"x")
        assert result.provider == "mock"
        assert result.metadata["environment"] == "development"

    def test_local_metadata_marks_production(self):
        result = LocalSigner().sign(b"x")
        assert result.provider == "local"
        assert result.metadata["environment"] == "production"
        assert result.metadata["algorithm"] == "SHA-256-RFC6234"

    def test_verify_after_sign_returns_true(self):
        signer = MockSigner()
        data = b"some content"
        result = signer.sign(data)
        assert signer.verify(data, result.pre_sign_hash) is True

    def test_verify_with_modified_document_returns_false(self):
        signer = MockSigner()
        original_data = b"original content"
        result = signer.sign(original_data)
        modified_data = b"modified content"
        assert signer.verify(modified_data, result.pre_sign_hash) is False

    def test_different_signers_produce_different_post_hash(self):
        data = b"same content"
        mock_post = MockSigner().sign(data).post_sign_hash
        local_post = LocalSigner().sign(data).post_sign_hash
        assert mock_post != local_post  # metadata differs (timestamp differs)


class TestSignerFactory:
    def test_default_returns_mock(self):
        with patch(
            "apps.legalization.signer.settings.SIGNATURE_PROVIDER",
            "mock",
            create=True,
        ):
            provider = SignerFactory.get_provider()
        assert isinstance(provider, MockSigner)

    def test_returns_local_by_name(self):
        provider = SignerFactory.get_provider("local")
        assert isinstance(provider, LocalSigner)

    def test_returns_mock_by_name(self):
        provider = SignerFactory.get_provider("mock")
        assert isinstance(provider, MockSigner)

    def test_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown signature provider"):
            SignerFactory.get_provider("does-not-exist")


# ---------------------------------------------------------------------------
# Integration tests via sign_legal_document
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
class TestSignLegalDocument(TestCase):
    def setUp(self):
        self.aspirante = _make_user(["R-ASPIRANTE"])
        self.convocatoria = _make_convocatoria()
        self.solicitud = _make_solicitud(self.convocatoria, self.aspirante)
        self.process = _make_process(self.convocatoria, self.aspirante)
        self.document = self.process.documents.first()
        self.document.pdf = _make_pdf("pagare.pdf")
        self.document.save()

    def test_persists_pre_and_post_hashes(self):
        pdf_bytes = b"%PDF-1.4 fake content for tests pagare.pdf"
        result = sign_legal_document(self.document, actor=self.aspirante)
        self.document.refresh_from_db()
        assert self.document.pre_sign_hash == hashlib.sha256(pdf_bytes).hexdigest()
        assert self.document.post_sign_hash == result.post_sign_hash
        assert self.document.signed_at is not None
        assert result.pre_sign_hash == hashlib.sha256(pdf_bytes).hexdigest()

    def test_idempotent_on_second_call(self):
        first = sign_legal_document(self.document, actor=self.aspirante)
        first_signed_at = self.document.signed_at
        first_post = self.document.post_sign_hash

        # Second call without changing the PDF.
        self.document.refresh_from_db()
        second = sign_legal_document(self.document, actor=self.aspirante)

        self.document.refresh_from_db()
        assert self.document.signed_at == first_signed_at
        assert self.document.post_sign_hash == first_post
        assert second.pre_sign_hash == first.pre_sign_hash
        assert second.post_sign_hash == first.post_sign_hash

    def test_creates_audit_event(self):
        sign_legal_document(self.document, actor=self.aspirante)
        events = AuditEvent.objects.filter(
            action="ELECTRONIC_SIGNATURE",
            module="legalization",
        )
        assert events.exists()
        latest = events.order_by("-timestamp").first()
        assert latest.entity_id == self.document.id
        assert latest.changes["pre_sign_hash"] == self.document.pre_sign_hash
        assert latest.changes["post_sign_hash"] == self.document.post_sign_hash

    def test_idempotent_does_not_create_duplicate_audit_event(self):
        sign_legal_document(self.document, actor=self.aspirante)
        count_after_first = AuditEvent.objects.filter(
            action="ELECTRONIC_SIGNATURE",
            module="legalization",
        ).count()

        self.document.refresh_from_db()
        sign_legal_document(self.document, actor=self.aspirante)
        count_after_second = AuditEvent.objects.filter(
            action="ELECTRONIC_SIGNATURE",
            module="legalization",
        ).count()
        assert count_after_first == count_after_second

    def test_empty_pdf_raises(self):
        empty_doc = self.process.documents.first()
        empty_doc.pdf = None
        empty_doc.save()
        with pytest.raises(ValueError, match="no tiene PDF cargado"):
            sign_legal_document(empty_doc, actor=self.aspirante)

    def test_convenience_sign_document_helper(self):
        """The module-level sign_document(b"x") helper still works."""
        result = sign_document(b"hello", document_type="test")
        assert result.pre_sign_hash == hashlib.sha256(b"hello").hexdigest()

    def test_convenience_verify_document_helper(self):
        """The module-level verify_document(b"x", h) helper still works."""
        data = b"hello"
        result = sign_document(data, document_type="t")
        assert verify_document(data, result.pre_sign_hash) is True
        assert verify_document(b"different", result.pre_sign_hash) is False
