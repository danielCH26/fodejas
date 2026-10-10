"""Tests for legalization HTMX views (CHG-302, CAP-009).

Tests:
  - List view: R-JUNTA sees all processes; beneficiary sees only own;
    unauthenticated → redirect
  - Detail view: process + documents in context; status badges; sign link
"""
from __future__ import annotations

import uuid

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import CustomUser, Role, UserRole
from apps.convocatories.models import Convocatory
from apps.legalization.models import LegalDocument, LegalizationProcess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user(email=None, role_codes=("R-JUNTA",)):
    email = email or f"{uuid.uuid4().hex}@example.com"
    user = CustomUser.objects.create(
        email=email,
        documento=uuid.uuid4().hex[:20],
        telefono="3000000000",
        first_name="Test",
        last_name="User",
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
        nombre="Convocatoria Prueba",
        codigo=f"CP-{uuid.uuid4().hex[:6].upper()}",
        tipo="cerrada",
        periodo="2026-1",
        monto_semestre_smlmv=5,
        duracion_maxima_semestres=10,
        cupo_total=10,
        estado=Convocatory.Estado.DEFINITIVA,
    )


def _make_process(convocatoria, beneficiary, status=LegalizationProcess.Status.PENDIENTE):
    process = LegalizationProcess.objects.create(
        beneficiary=beneficiary,
        convocatoria=convocatoria,
        status=status,
    )
    for doc_type, _ in LegalDocument.DocumentType.choices:
        LegalDocument.objects.create(
            process=process,
            document_type=doc_type,
            status=LegalDocument.Status.PENDIENTE,
        )
    return process


def _session_client(user):
    """Return a Django test Client logged in as user via session."""
    client = Client()
    client.force_login(user)
    return client


# ---------------------------------------------------------------------------
# List view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLegalizationListView:
    """GET /legalization/ (the list view)."""

    def test_junta_sees_all_processes(self):
        """R-JUNTA sees all processes from all beneficiaries."""
        junta = _make_user("junta@example.com", ["R-JUNTA"])
        asp1 = _make_user("asp1@example.com", ["R-ASPIRANTE"])
        asp2 = _make_user("asp2@example.com", ["R-ASPIRANTE"])
        conv = _make_convocatoria()
        _make_process(conv, asp1)
        _make_process(conv, asp2)

        client = _session_client(junta)
        url = reverse("legalization:list")
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["processes"].count() == 2

    def test_beneficiary_sees_only_own_process(self):
        """An Aspirante sees only their own processes."""
        asp = _make_user("asp@example.com", ["R-ASPIRANTE"])
        other = _make_user("other@example.com", ["R-ASPIRANTE"])
        conv = _make_convocatoria()
        _make_process(conv, asp)
        _make_process(conv, other)

        client = _session_client(asp)
        url = reverse("legalization:list")
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["processes"].count() == 1
        assert response.context["processes"].first().beneficiary == asp

    def test_unauthenticated_returns_302(self):
        """An unauthenticated request redirects to login."""
        client = Client()
        url = reverse("legalization:list")
        response = client.get(url)
        assert response.status_code == 302

    def test_other_aspirante_cannot_see_beneficiary_process(self):
        """An Aspirante cannot see another beneficiary's process via list."""
        asp1 = _make_user("asp1@example.com", ["R-ASPIRANTE"])
        asp2 = _make_user("asp2@example.com", ["R-ASPIRANTE"])
        conv = _make_convocatoria()
        _make_process(conv, asp1)

        client = _session_client(asp2)
        url = reverse("legalization:list")
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["processes"].count() == 0


# ---------------------------------------------------------------------------
# Detail view
# ---------------------------------------------------------------------------

@pytest.mark.django_db
class TestLegalizationDetailView:
    """GET /legalization/process/<uuid:pk>/."""

    def test_junta_can_access_any_process(self):
        """R-JUNTA can view any beneficiary's process detail."""
        junta = _make_user("junta@example.com", ["R-JUNTA"])
        asp = _make_user("asp@example.com", ["R-ASPIRANTE"])
        conv = _make_convocatoria()
        process = _make_process(conv, asp)

        client = _session_client(junta)
        url = reverse("legalization:detail", kwargs={"pk": process.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert "process" in response.context

    def test_beneficiary_can_access_own_process(self):
        """A beneficiary can view their own process detail."""
        asp = _make_user("asp@example.com", ["R-ASPIRANTE"])
        conv = _make_convocatoria()
        process = _make_process(conv, asp)

        client = _session_client(asp)
        url = reverse("legalization:detail", kwargs={"pk": process.pk})
        response = client.get(url)
        assert response.status_code == 200
        assert response.context["process"] == process

    def test_beneficiary_cannot_access_other_process(self):
        """An Aspirante cannot access another beneficiary's process detail."""
        asp1 = _make_user("asp1@example.com", ["R-ASPIRANTE"])
        asp2 = _make_user("asp2@example.com", ["R-ASPIRANTE"])
        conv = _make_convocatoria()
        process = _make_process(conv, asp1)

        client = _session_client(asp2)
        url = reverse("legalization:detail", kwargs={"pk": process.pk})
        assert client.get(url).status_code == 404

    def test_detail_context_contains_documents(self):
        """Detail view context includes all process documents."""
        asp = _make_user("asp@example.com", ["R-ASPIRANTE"])
        conv = _make_convocatoria()
        process = _make_process(conv, asp)

        client = _session_client(asp)
        url = reverse("legalization:detail", kwargs={"pk": process.pk})
        response = client.get(url)
        assert response.status_code == 200
        doc_types = {d.document_type for d in response.context["process"].documents.all()}
        assert doc_types == {
            LegalDocument.DocumentType.PAGARE,
            LegalDocument.DocumentType.CARTA_INSTRUCCIONES,
            LegalDocument.DocumentType.CONTRATO,
            LegalDocument.DocumentType.ACTO_ADMINISTRATIVO,  # CHG-303
        }

    def test_detail_document_status_badges(self):
        """Detail template renders document status badges (Pendiente/Firmado/Legalizado)."""
        asp = _make_user("asp@example.com", ["R-ASPIRANTE"])
        conv = _make_convocatoria()
        process = _make_process(conv, asp)
        docs = list(process.documents.all())
        docs[0].status = LegalDocument.Status.PENDIENTE
        docs[0].save()
        docs[1].status = LegalDocument.Status.FIRMADO
        docs[1].save()
        docs[2].status = LegalDocument.Status.LEGALIZADO
        docs[2].save()

        client = _session_client(asp)
        url = reverse("legalization:detail", kwargs={"pk": process.pk})
        response = client.get(url)
        assert response.status_code == 200
        html = response.content.decode()
        # Template uses get_status_display() → Spanish labels.
        assert "Pendiente" in html
        assert "Firmado" in html
        assert "Legalizado" in html
