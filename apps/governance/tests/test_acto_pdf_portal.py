"""Tests for CHG-207 pendings: acto PDF generation, public portal
access control, and the administrative act end-to-end flow.

WeasyPrint cannot render on this host (GTK libs absent) — PDF bytes
are provided via a renderer seam, mirroring apps/legalization tests.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.condonation.models import Sanction  # noqa: F401 — import guard for app wiring
from apps.convocatories.models import Convocatory
from apps.governance.models import ActoAdministrativo, ListadoDefinitivo
from apps.governance.services.pdf import guardar_pdf_acto

User = get_user_model()


def _junta_user(n=1):
    return User.objects.create_user(
        email=f"synthetic-junta-{n}@example.test",
        documento=f"9876543{n:04d}",
        password="test-password-not-real",
        first_name="Presidente",
        last_name="Junta",
        is_staff=True,
        is_superuser=True,
    )


def _make_acto(estado=ActoAdministrativo.Estado.FIRMADO, n=1):
    from datetime import date

    return ActoAdministrativo.objects.create(
        numero=f"SED-FODEJAS-2026-{n:04d}",
        tipo=ActoAdministrativo.Tipo.RESOLUCION,
        estado=estado,
        fecha_expedicion=date(2026, 1, 15),
        firmantes=["Presidente JA", "Secretario de Educación"],
    )


def _seam_pdf(monkeypatch, content=b"%PDF-1.4 synthetic acto"):
    """Patch WeasyPrint import inside governance pdf service."""

    class _FakeHTML:
        def __init__(self, string=None):
            self.string = string

        def write_pdf(self):
            return content

    import apps.governance.services.pdf as pdf_module

    class _FakeModule:
        HTML = _FakeHTML

    monkeypatch.setattr(pdf_module, "HTML", _FakeHTML, raising=False)
    # generar_pdf_acto imports weasyprint lazily; patch the import path
    import sys

    monkeypatch.setitem(sys.modules, "weasyprint", _FakeModule)


@pytest.mark.django_db
class TestActoPdf:
    def test_guardar_pdf_almacena_hash_sha256(self, db, monkeypatch):
        acto = _make_acto()
        _seam_pdf(monkeypatch, b"%PDF-1.4 acto-bytes-abc")
        sha = guardar_pdf_acto(acto)
        acto.refresh_from_db()
        import hashlib

        assert sha == hashlib.sha256(b"%PDF-1.4 acto-bytes-abc").hexdigest()
        assert acto.pdf_sha256 == sha
        assert acto.pdf.name.endswith(".pdf")

    def test_pdf_bytes_depends_on_acto_content(self, db, monkeypatch):
        acto = _make_acto()
        captured = {}

        class _FakeHTML:
            def __init__(self, string=None):
                captured["html"] = string

            def write_pdf(self):
                return captured["html"].encode("utf-8")

        import sys

        class _FakeModule:
            HTML = _FakeHTML

        monkeypatch.setitem(sys.modules, "weasyprint", _FakeModule)
        guardar_pdf_acto(acto)
        # The rendered HTML must reference the act number and institution.
        assert "SED-FODEJAS-2026-0001" in captured["html"]
        assert "Secretaría de Educación Departamental" in captured["html"]


@pytest.mark.django_db
class TestPortalPublico:
    def test_anonymous_access_allowed(self, db):
        client = Client()
        response = client.get(reverse("governance:resultados_publicos"))
        assert response.status_code == 200

    def test_only_published_actos_listed(self, db):
        publicado = _make_acto(estado=ActoAdministrativo.Estado.PUBLICADO, n=2)
        firmado = _make_acto(estado=ActoAdministrativo.Estado.FIRMADO, n=3)
        for acto_, n in ((publicado, 1), (firmado, 2)):
            conv = Convocatory.objects.create(
                codigo=f"CHG-207-PORTAL-{n}",
                nombre=f"Conv Portal {n}",
                estado=Convocatory.Estado.EN_INSCRIPCION,
            )
            ListadoDefinitivo.objects.create(convocatoria=conv, acto=acto_, ranking=[])
        client = Client()
        response = client.get(reverse("governance:resultados_publicos"))
        listados = list(response.context["listados"])
        # The portal returns dicts keyed by the LISTADO uuid (no PII:
        # rank/radicado only). Gating: only listados whose acto is
        # PUBLICADO appear.
        shown_uuids = {str(item["uuid"]) for item in listados}
        listado_publicado = ListadoDefinitivo.objects.get(acto=publicado)
        listado_firmado = ListadoDefinitivo.objects.get(acto=firmado)
        assert str(listado_publicado.uuid) in shown_uuids
        assert str(listado_firmado.uuid) not in shown_uuids


@pytest.mark.django_db
class TestActoEndToEnd:
    def test_full_acto_flow_pdf_and_hash(self, db, monkeypatch):
        """crear (ORM) → firmar (view) → PDF+hash → publicar (view) → portal."""
        from datetime import date

        user = _junta_user()
        client = Client()
        client.force_login(user)

        # 1. Create (ORM with real model fields)
        acto = ActoAdministrativo.objects.create(
            numero="SED-FODEJAS-2026-0100",
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion=date(2026, 1, 15),
            asunto="Resolución sintética de otorgamiento",
            estado=ActoAdministrativo.Estado.BORRADOR,
        )
        assert acto.estado == ActoAdministrativo.Estado.BORRADOR

        # 2. Sign through the real view
        client.post(
            reverse("governance:acto_sign", kwargs={"pk": acto.uuid}),
            {"firmantes_csv": "Presidente JA,Secretario de Educación"},
            follow=True,
        )
        acto.refresh_from_db()
        assert acto.estado == ActoAdministrativo.Estado.FIRMADO

        # 3. Generate PDF (seam) — hash must be stored
        _seam_pdf(monkeypatch, b"%PDF-1.4 e2e-acto")
        sha = guardar_pdf_acto(acto)
        acto.refresh_from_db()
        assert acto.pdf_sha256 == sha

        # 4. Publish through the real view
        client.post(reverse("governance:acto_publish", kwargs={"pk": acto.uuid}), follow=True)
        acto.refresh_from_db()
        assert acto.estado == ActoAdministrativo.Estado.PUBLICADO

        # 5. Anonymous citizen reaches the public portal
        anon = Client()
        response = anon.get(reverse("governance:resultados_publicos"))
        assert response.status_code == 200
