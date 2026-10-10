"""Tests for LegalizationService (CHG-302, CAP-009).

Tests the workflow methods:
  - create_documents_for_beneficiary()
  - generate_pdf()
  - complete_legalization()
  - cancel_document()

Also tests the domain transitions module.
"""
import datetime
import hashlib

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import CustomUser, Role, UserRole
from apps.audit.models import AuditEvent
from apps.convocatories.models import Convocatory
from apps.legalization.domain import transitions as trans
from apps.legalization.models import LegalDocument, LegalizationProcess
from apps.legalization.services import LegalizationService, sign_legal_document

# ---------------------------------------------------------------------------
# Fixture helpers (mirrors test_signer.py style)
# ---------------------------------------------------------------------------

def _make_user(email=None, role_codes=("R-JUNTA",)):
    import uuid as _u
    email = email or f"{_u.uuid4().hex}@example.com"
    user = CustomUser.objects.create(
        email=email,
        documento=_u.uuid4().hex[:20],
        telefono="3000000000",
        first_name="Aspirante",
        last_name="Ejemplo",
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
        nombre="Convocatoria Test CHG-302",
        codigo="CT-2026-CHG302",
        tipo="cerrada",
        periodo="2026-1",
        monto_semestre_smlmv=5,
        duracion_maxima_semestres=10,
        cupo_total=10,
        estado=Convocatory.Estado.DEFINITIVA,
    )


def _pdf_bytes(name=b"test.pdf") -> bytes:
    return b"%PDF-1.4 fake pdf content " + name


def _dt(year=2026, month=1, day=15):
    """Return a timezone-aware datetime for template contexts."""
    return datetime.datetime(year, month, day, tzinfo=datetime.UTC)


# ---------------------------------------------------------------------------
# LegalizationService — create_documents_for_beneficiary
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCreateDocumentsForBeneficiary:
    def test_creates_process_and_three_documents(self):
        user = _make_user()
        conv = _make_convocatoria()

        docs = LegalizationService.create_documents_for_beneficiary(user, conv)

        assert len(docs) == 4  # CHG-303: +ACTO_ADMINISTRATIVO
        assert LegalDocument.DocumentType.PAGARE in docs
        assert LegalDocument.DocumentType.CARTA_INSTRUCCIONES in docs
        assert LegalDocument.DocumentType.CONTRATO in docs
        assert LegalDocument.DocumentType.ACTO_ADMINISTRATIVO in docs  # CHG-303
        for doc in docs.values():
            assert doc.status == LegalDocument.Status.PENDIENTE
            assert doc.pre_sign_hash == ""
            assert doc.post_sign_hash == ""

    def test_idempotent_same_user_and_convocatoria(self):
        user = _make_user()
        conv = _make_convocatoria()

        first = LegalizationService.create_documents_for_beneficiary(user, conv)
        second = LegalizationService.create_documents_for_beneficiary(user, conv)

        # Same process returned.
        assert (
            first[LegalDocument.DocumentType.PAGARE].process_id
            == second[LegalDocument.DocumentType.PAGARE].process_id
        )
        # No extra documents created.
        assert (
            LegalDocument.objects.filter(
                process_id=first[LegalDocument.DocumentType.PAGARE].process_id
            ).count()
            == 4  # CHG-303: +ACTO_ADMINISTRATIVO
        )

    def test_different_users_create_separate_processes(self):
        user1 = _make_user(f"u1-{__name__}@example.com")
        user2 = _make_user(f"u2-{__name__}@example.com")
        conv = _make_convocatoria()

        docs1 = LegalizationService.create_documents_for_beneficiary(user1, conv)
        docs2 = LegalizationService.create_documents_for_beneficiary(user2, conv)

        assert (
            docs1[LegalDocument.DocumentType.PAGARE].process_id
            != docs2[LegalDocument.DocumentType.PAGARE].process_id
        )


# ---------------------------------------------------------------------------
# LegalizationService — generate_pdf (seam strategy)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestGeneratePdf:
    def _base_context(self, conv):
        return {
            "convocatoria": conv.codigo,
            "radicado": "RAD-TEST-001",
            "nombre_beneficiario": "Aspirante Ejemplo",
            "documento_beneficiario": "12345678",
            "direccion_beneficiario": "San Andrés, Isla",
            "nombre_codeudor": "Familiar Ejemplo",
            "documento_codeudor": "87654321",
            "direccion_codeudor": "San Andrés, Isla",
            "nombre_programa": "Ingeniería de Sistemas",
            "nombre_institucion": "Universidad Nacional",
            "monto_total": 5000000,
            "duracion_semestres": 10,
            "periodo_beneficio": 5,
            "fecha_emision": _dt(),
            "pre_sign_hash": "",
            "cuotas": [],
        }

    def _render(self, doc, context):
        """Call generate_pdf with WeasyPrint patched to return controlled bytes."""
        fake_pdf = _pdf_bytes()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("apps.legalization.services._WASYPRINT_AVAILABLE", True)
            import apps.legalization.services as svc
            original_wh = svc._WeasyHTML
            class FakeWeasyHTML:
                def __init__(self, string=None, **kw):
                    pass
                def write_pdf(self):
                    return fake_pdf
            svc._WeasyHTML = FakeWeasyHTML
            try:
                return LegalizationService.generate_pdf(doc, context)
            finally:
                svc._WeasyHTML = original_wh

    def test_render_pagare_template(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)
        pagare = docs[LegalDocument.DocumentType.PAGARE]

        result = self._render(pagare, self._base_context(conv))

        assert result.pdf is not None
        assert result.pre_sign_hash == hashlib.sha256(_pdf_bytes()).hexdigest()
        assert result.pre_sign_hash != ""

    def test_generate_pdf_stores_correct_hash(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)
        doc = docs[LegalDocument.DocumentType.CARTA_INSTRUCCIONES]

        result = self._render(doc, self._base_context(conv))

        assert result.pre_sign_hash == hashlib.sha256(_pdf_bytes()).hexdigest()

    def test_generate_pdf_logs_audit_event(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)
        doc = docs[LegalDocument.DocumentType.CONTRATO]

        self._render(doc, self._base_context(conv))

        events = AuditEvent.objects.filter(
            action="GENERATE_PDF",
            module="legalization",
            entity_id=str(doc.id),
        )
        assert events.exists()
        assert events.first().changes["pre_sign_hash"] == hashlib.sha256(
            _pdf_bytes()
        ).hexdigest()

    def test_raises_for_unknown_document_type(self):
        """A document with a bogus document_type is rejected before WeasyPrint."""
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)
        doc = docs[LegalDocument.DocumentType.PAGARE]
        doc.document_type = "NOEXISTE"
        doc.save()

        with pytest.raises(ValueError, match="Unknown document_type"):
            LegalizationService.generate_pdf(doc, {})

    def test_raises_when_weasyprint_unavailable(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)
        doc = docs[LegalDocument.DocumentType.PAGARE]

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("apps.legalization.services._WASYPRINT_AVAILABLE", False)
            import apps.legalization.services as svc
            original_wh = svc._WeasyHTML
            svc._WeasyHTML = None
            try:
                with pytest.raises(RuntimeError, match="WeasyPrint is not available"):
                    LegalizationService.generate_pdf(doc, {})
            finally:
                svc._WeasyHTML = original_wh

    def test_template_context_renders_all_three_documents(self):
        """Smoke test: all three templates render without raising."""
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)

        for doc_type in LegalDocument.DocumentType.values:
            doc = docs[doc_type]
            result = self._render(doc, self._base_context(conv))
            assert result.pre_sign_hash != ""


# ---------------------------------------------------------------------------
# LegalizationService — complete_legalization
# ---------------------------------------------------------------------------

def _sign_document(document, actor=None):
    """Helper: attach a fake PDF and call sign_legal_document."""
    document.pdf.save(
        "test.pdf",
        SimpleUploadedFile("test.pdf", _pdf_bytes(), content_type="application/pdf"),
        save=False,
    )
    document.pre_sign_hash = hashlib.sha256(_pdf_bytes()).hexdigest()
    document.save(update_fields=["pdf", "pre_sign_hash"])
    return sign_legal_document(document, actor=actor)


@pytest.mark.django_db
class TestCompleteLegalization:
    def test_all_firmado_transitions_to_legalizado(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)

        for doc in docs.values():
            _sign_document(doc, actor=user)

        process = docs[LegalDocument.DocumentType.PAGARE].process
        result = LegalizationService.complete_legalization(process, actor=user)

        assert result.status == LegalizationProcess.Status.LEGALIZADO
        assert result.completed_at is not None
        for doc in docs.values():
            doc.refresh_from_db()
            assert doc.status == LegalDocument.Status.LEGALIZADO

    def test_raises_when_document_not_firmado(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)

        # Only sign three of four — ACTO_ADMINISTRATIVO stays PENDIENTE (CHG-303).
        _sign_document(docs[LegalDocument.DocumentType.PAGARE], actor=user)
        _sign_document(docs[LegalDocument.DocumentType.CARTA_INSTRUCCIONES], actor=user)
        _sign_document(docs[LegalDocument.DocumentType.CONTRATO], actor=user)
        # ACTO_ADMINISTRATIVO still PENDIENTE.

        process = docs[LegalDocument.DocumentType.PAGARE].process
        with pytest.raises(ValueError, match="not FIRMADO"):
            LegalizationService.complete_legalization(process, actor=user)

    def test_raises_when_document_cancelled(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)

        _sign_document(docs[LegalDocument.DocumentType.PAGARE], actor=user)
        _sign_document(docs[LegalDocument.DocumentType.CARTA_INSTRUCCIONES], actor=user)
        _sign_document(docs[LegalDocument.DocumentType.CONTRATO], actor=user)
        # ACTO_ADMINISTRATIVO is CANCELLED (CHG-303).
        docs[LegalDocument.DocumentType.ACTO_ADMINISTRATIVO].status = (
            LegalDocument.Status.CANCELADO
        )
        docs[LegalDocument.DocumentType.ACTO_ADMINISTRATIVO].save()

        process = docs[LegalDocument.DocumentType.PAGARE].process
        with pytest.raises(ValueError, match="not FIRMADO"):
            LegalizationService.complete_legalization(process, actor=user)

    def test_idempotent_on_already_legalizado(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)

        for doc in docs.values():
            _sign_document(doc, actor=user)
        process = docs[LegalDocument.DocumentType.PAGARE].process
        LegalizationService.complete_legalization(process, actor=user)

        initial_count = AuditEvent.objects.filter(
            action="LEGALIZATION_COMPLETE",
            module="legalization",
        ).count()

        # Second call is a no-op.
        result = LegalizationService.complete_legalization(process, actor=user)
        assert result.status == LegalizationProcess.Status.LEGALIZADO

        # No duplicate audit events.
        assert (
            AuditEvent.objects.filter(
                action="LEGALIZATION_COMPLETE",
                module="legalization",
            ).count()
            == initial_count
        )

    def test_raises_on_empty_process(self):
        user = _make_user()
        conv = _make_convocatoria()
        process = LegalizationProcess.objects.create(
            beneficiary=user,
            convocatoria=conv,
            status=LegalizationProcess.Status.PENDIENTE,
        )
        with pytest.raises(ValueError, match="no documents"):
            LegalizationService.complete_legalization(process, actor=user)

    def test_logs_audit_event_per_document(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)

        for doc in docs.values():
            _sign_document(doc, actor=user)
        process = docs[LegalDocument.DocumentType.PAGARE].process
        LegalizationService.complete_legalization(process, actor=user)

        for doc in docs.values():
            event = AuditEvent.objects.filter(
                action="LEGALIZATION_COMPLETE",
                entity_id=str(doc.id),
                module="legalization",
            ).first()
            assert event is not None
            assert event.changes["new_status"] == LegalDocument.Status.LEGALIZADO


# ---------------------------------------------------------------------------
# LegalizationService — cancel_document
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestCancelDocument:
    def test_cancel_pendiente_document(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)
        pagare = docs[LegalDocument.DocumentType.PAGARE]

        result = LegalizationService.cancel_document(pagare, actor=user)

        assert result.status == LegalDocument.Status.CANCELADO
        pagare.refresh_from_db()
        assert pagare.status == LegalDocument.Status.CANCELADO

    def test_cancel_firmado_document_allowed(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)
        pagare = docs[LegalDocument.DocumentType.PAGARE]
        _sign_document(pagare, actor=user)

        result = LegalizationService.cancel_document(pagare, actor=user)

        assert result.status == LegalDocument.Status.CANCELADO

    def test_cannot_cancel_legalizado_document(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)
        pagare = docs[LegalDocument.DocumentType.PAGARE]
        _sign_document(pagare, actor=user)
        pagare.status = LegalDocument.Status.LEGALIZADO
        pagare.save()

        with pytest.raises(ValueError, match="terminal"):
            LegalizationService.cancel_document(pagare, actor=user)

    def test_cannot_cancel_already_cancelled_document(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)
        pagare = docs[LegalDocument.DocumentType.PAGARE]
        LegalizationService.cancel_document(pagare, actor=user)

        with pytest.raises(ValueError, match="terminal"):
            LegalizationService.cancel_document(pagare, actor=user)

    def test_cancel_logs_audit_event(self):
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)
        pagare = docs[LegalDocument.DocumentType.PAGARE]

        LegalizationService.cancel_document(pagare, actor=user)

        event = AuditEvent.objects.filter(
            action="DOCUMENT_CANCELLED",
            entity_id=str(pagare.id),
            module="legalization",
        ).first()
        assert event is not None
        assert event.changes["old_status"] == LegalDocument.Status.PENDIENTE
        assert event.changes["new_status"] == LegalDocument.Status.CANCELADO


# ---------------------------------------------------------------------------
# Domain transitions
# ---------------------------------------------------------------------------

class TestDocumentTransitions:
    def test_pendiente_can_transition_to_firmado_and_cancelled(self):
        assert trans.is_valid_document_transition(
            LegalDocument.Status.PENDIENTE,
            LegalDocument.Status.FIRMADO,
        )
        assert trans.is_valid_document_transition(
            LegalDocument.Status.PENDIENTE,
            LegalDocument.Status.CANCELADO,
        )

    def test_firmado_can_transition_to_legalizado_and_cancelled(self):
        assert trans.is_valid_document_transition(
            LegalDocument.Status.FIRMADO,
            LegalDocument.Status.LEGALIZADO,
        )
        assert trans.is_valid_document_transition(
            LegalDocument.Status.FIRMADO,
            LegalDocument.Status.CANCELADO,
        )

    def test_terminal_states_have_no_outgoing_transitions(self):
        assert not trans.is_valid_document_transition(
            LegalDocument.Status.LEGALIZADO,
            LegalDocument.Status.FIRMADO,
        )
        assert not trans.is_valid_document_transition(
            LegalDocument.Status.CANCELADO,
            LegalDocument.Status.FIRMADO,
        )

    def test_is_document_terminal(self):
        assert trans.is_document_terminal(LegalDocument.Status.LEGALIZADO)
        assert trans.is_document_terminal(LegalDocument.Status.CANCELADO)
        assert not trans.is_document_terminal(LegalDocument.Status.PENDIENTE)
        assert not trans.is_document_terminal(LegalDocument.Status.FIRMADO)

    def test_get_valid_document_transitions(self):
        assert (
            LegalDocument.Status.FIRMADO
            in trans.get_valid_document_transitions(LegalDocument.Status.PENDIENTE)
        )
        assert (
            LegalDocument.Status.LEGALIZADO
            in trans.get_valid_document_transitions(LegalDocument.Status.FIRMADO)
        )
        assert trans.get_valid_document_transitions(
            LegalDocument.Status.LEGALIZADO
        ) == set()


class TestProcessTransitions:
    def test_pendiente_can_transition_to_en_proceso_and_cancelled(self):
        assert trans.is_valid_process_transition(
            LegalizationProcess.Status.PENDIENTE,
            LegalizationProcess.Status.EN_PROCESO,
        )
        assert trans.is_valid_process_transition(
            LegalizationProcess.Status.PENDIENTE,
            LegalizationProcess.Status.CANCELADO,
        )

    def test_en_proceso_can_transition_to_legalizado_and_cancelled(self):
        assert trans.is_valid_process_transition(
            LegalizationProcess.Status.EN_PROCESO,
            LegalizationProcess.Status.LEGALIZADO,
        )

    def test_terminal_process_states(self):
        assert trans.is_process_terminal(LegalizationProcess.Status.LEGALIZADO)
        assert trans.is_process_terminal(LegalizationProcess.Status.CANCELADO)
        assert not trans.is_process_terminal(LegalizationProcess.Status.EN_PROCESO)

    def test_get_valid_process_transitions(self):
        assert (
            LegalizationProcess.Status.EN_PROCESO
            in trans.get_valid_process_transitions(
                LegalizationProcess.Status.PENDIENTE
            )
        )
        assert trans.get_valid_process_transitions(
            LegalizationProcess.Status.LEGALIZADO
        ) == set()


# ---------------------------------------------------------------------------
# Post-sign hash tamper detection (D3 / tasks.md 5.3)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestPostSignTamperDetection:
    def test_signing_modified_pdf_produces_different_post_hash(self):
        """If the PDF is modified after generate_pdf, signing produces a new
        post_sign_hash, proving the document was tampered with post-generation.

        The pre_sign_hash recorded at PDF-generation time anchors integrity.
        A modified file will have a different pre_hash at signing time,
        causing the idempotency guard to be bypassed and a new post_sign_hash
        to be computed — different from the original.
        """
        user = _make_user()
        conv = _make_convocatoria()
        docs = LegalizationService.create_documents_for_beneficiary(user, conv)
        doc = docs[LegalDocument.DocumentType.PAGARE]

        # Generate PDF — stores pre_sign_hash.
        fake_pdf = _pdf_bytes()
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("apps.legalization.services._WASYPRINT_AVAILABLE", True)
            import apps.legalization.services as svc
            original_wh = svc._WeasyHTML

            class FakeWeasyHTML:
                def __init__(self, string=None, **kw):
                    pass

                def write_pdf(self):
                    return fake_pdf

            svc._WeasyHTML = FakeWeasyHTML
            try:
                LegalizationService.generate_pdf(doc, {})
            finally:
                svc._WeasyHTML = original_wh

        original_hash = doc.pre_sign_hash
        assert original_hash != ""

        # Tamper: overwrite the PDF with different bytes.
        tampered_pdf = b"%PDF-1.4 TAMPERED CONTENT " + b"x" * 100
        doc.pdf.save(
            "tampered.pdf",
            SimpleUploadedFile(
                "tampered.pdf",
                tampered_pdf,
                content_type="application/pdf",
            ),
            save=True,
        )
        doc.refresh_from_db()

        # pre_sign_hash on the model is unchanged.
        assert doc.pre_sign_hash == original_hash
        # But the file is different.
        assert hashlib.sha256(tampered_pdf).hexdigest() != original_hash

        # sign_legal_document computes fresh pre_hash from the tampered file.
        result = sign_legal_document(doc, actor=user)

        # post_sign_hash is based on tampered bytes, proving the tamper.
        assert result.pre_sign_hash == hashlib.sha256(tampered_pdf).hexdigest()
        assert result.pre_sign_hash != original_hash
