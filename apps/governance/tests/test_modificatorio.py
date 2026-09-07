"""CPACA Art. 45 acto modificatorio tests (CHG-208)."""
from __future__ import annotations

import pytest
from django.test import TestCase

from apps.accounts.models import CustomUser, Role, UserRole
from apps.convocatories.models import Convocatory
from apps.governance.domain.transitions import crear_modificatorio
from apps.governance.models import ActoAdministrativo
from apps.governance.services.generador import generar_numero_acto


def _make_role(code="R-JUNTA"):
    role, _ = Role.objects.get_or_create(
        code=code,
        defaults={"name": code, "type": "interno", "description": code},
    )
    return role


def _make_user(email="junta@example.com", codes=("R-JUNTA",)):
    import uuid as uuidlib

    user = CustomUser.objects.create(
        email=email,
        documento=uuidlib.uuid4().hex[:20],
        telefono="3000000000",
    )
    for code in codes:
        role = _make_role(code)
        UserRole.objects.get_or_create(
            user=user, role=role, convocation_scope_id=None
        )
    return user


def _make_convocatoria():
    return Convocatory.objects.create(
        nombre="Convocatoria Modificatorio",
        codigo="CM-2026-001",
        tipo="cerrada",
        periodo="2026-1",
        monto_semestre_smlmv=5,
        duracion_maxima_semestres=10,
        cupo_total=10,
        estado=Convocatory.Estado.DEFINITIVA,
    )


@pytest.mark.django_db(transaction=True)
class TestModificatorio(TestCase):
    """CPACA Art. 45: actos modificatorios reference an original."""

    def setUp(self):
        self.user = _make_user()
        self.convocatoria = _make_convocatoria()

    def test_create_modificatorio_inherits_convocatoria(self):
        original = ActoAdministrativo.objects.create(
            numero=generar_numero_acto("resolucion"),
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion="2026-09-05",
            asunto="Original",
            considerandos=[{"numeral": "1", "texto": "X"}],
            resolutivo="Se resuelve.",
            convocatoria=self.convocatoria,
            estado=ActoAdministrativo.Estado.FIRMADO,
        )
        modificatorio = crear_modificatorio(
            original.uuid,
            asunto="Corrigiendo artículo 3",
            considerandos=[
                {"numeral": "1", "texto": "Se detectó error formal"},
            ],
            resolutivo="Modifíquese el artículo 3 en el sentido de…",
        )
        self.assertEqual(modificatorio.tipo, ActoAdministrativo.Tipo.MODIFICATORIO)
        self.assertEqual(modificatorio.convocatoria_id, original.convocatoria_id)
        self.assertEqual(modificatorio.acto_original_id, original.id)
        self.assertEqual(modificatorio.estado, ActoAdministrativo.Estado.BORRADOR)
        # numero comes from the "modificatorio" sequence, not "resolucion"
        self.assertTrue(modificatorio.numero.startswith("FODEJAS-"))

    def test_modificatorio_requires_original_not_modificatorio(self):
        original = ActoAdministrativo.objects.create(
            numero=generar_numero_acto("resolucion"),
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion="2026-09-05",
            asunto="Original",
            considerandos=[{"numeral": "1", "texto": "X"}],
            resolutivo="Se resuelve.",
            convocatoria=self.convocatoria,
            estado=ActoAdministrativo.Estado.FIRMADO,
        )
        first_modificatorio = crear_modificatorio(
            original.uuid,
            asunto="Primer modificatorio",
            considerandos=[{"numeral": "1", "texto": "Y"}],
            resolutivo="Modifíquese.",
        )

        with self.assertRaises(ValueError) as ctx:
            crear_modificatorio(
                first_modificatorio.uuid,
                asunto="Segundo modificatorio (sobre modificatorio)",
                considerandos=[{"numeral": "1", "texto": "Z"}],
                resolutivo="Modifíquese de nuevo.",
            )
        self.assertIn("no se puede crear un modificatorio de otro", str(ctx.exception))

    def test_modificatorio_number_uses_modificatorio_sequence(self):
        original = ActoAdministrativo.objects.create(
            numero=generar_numero_acto("resolucion"),
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion="2026-09-05",
            asunto="Original",
            considerandos=[{"numeral": "1", "texto": "X"}],
            resolutivo="Se resuelve.",
            convocatoria=self.convocatoria,
            estado=ActoAdministrativo.Estado.FIRMADO,
        )
        m = crear_modificatorio(
            original.uuid,
            asunto="Modificatorio",
            considerandos=[],
            resolutivo="Resolutivo.",
        )
        # Numbering sequence is per-tipo-per-year; first modificatorio
        # of the year → FODEJAS-YYYY-00001.
        self.assertTrue(m.numero.endswith("-00001"))
