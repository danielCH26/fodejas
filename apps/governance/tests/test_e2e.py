"""End-to-end tests for CHG-207 definitive results flow."""
import pytest
from django.test import TestCase, Client
from django.utils import timezone
from django.urls import reverse

from apps.accounts.models import CustomUser
from apps.convocatories.models import Convocatory
from apps.applications.models import Solicitud
from apps.scoring.models import PuntajeTotal, Evaluacion
from apps.governance.models import (
    ActoAdministrativo,
    ListadoDefinitivo,
    SecuencialActo,
)
from apps.governance.services.generador import generar_numero_acto
from apps.governance.services.listado import (
    obtener_ranking_final,
    generar_listado_definitivo,
)


class TestFlujoResultadosDefinitivosE2E(TestCase):
    """E2E tests for the complete definitive results flow.

    Flow tested:
    1. Scoring -> Generate scores for solicitudes
    2. Acto administrativo -> Create act with sequential number
    3. Listado definitivo -> Generate ranking and create listing
    4. Publicación -> Verify public view without PII
    """

    def setUp(self):
        """Set up test data."""
        # Clean up any existing test data
        SecuencialActo.objects.all().delete()
        ActoAdministrativo.objects.all().delete()
        ListadoDefinitivo.objects.all().delete()
        Convocatory.objects.all().delete()
        Solicitud.objects.all().delete()
        CustomUser.objects.filter(documento__startswith="TEST").delete()

        # Create admin user
        self.admin_user = CustomUser.objects.create_user(
            documento="TEST_ADMIN001",
            email="admin@test.com",
            password="testpass123",
            is_staff=True,
        )

        # Create convocatoria
        self.convocatoria = Convocatory.objects.create(
            nombre="Convocatoria Prueba 2026-1",
            codigo="prueba-2026-1",
            tipo=Convocatory.Tipo.PUBLICA,
            periodo="2026-1",
            estado=Convocatory.Estado.EN_CALIFICACION,
            fecha_apertura=timezone.now(),
            fecha_cierre=timezone.now(),
        )

        # Create applicants (aspirantes) using CustomUser
        self.aspirante1 = CustomUser.objects.create_user(
            documento="TEST_ASPIR001",
            email="aspirante1@test.com",
            password="testpass123",
            first_name="Juan",
            last_name="Perez",
        )

        self.aspirante2 = CustomUser.objects.create_user(
            documento="TEST_ASPIR002",
            email="aspirante2@test.com",
            password="testpass123",
            first_name="Maria",
            last_name="Garcia",
        )

        self.aspirante3 = CustomUser.objects.create_user(
            documento="TEST_ASPIR003",
            email="aspirante3@test.com",
            password="testpass123",
            first_name="Carlos",
            last_name="Rodriguez",
        )

        # Create solicitudes (applications) in verified state
        self.solicitud1 = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.aspirante1,
            estado=Solicitud.Estado.VERIFICADA,
            radicado="FODEJAS-2026-00001",
        )

        self.solicitud2 = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.aspirante2,
            estado=Solicitud.Estado.VERIFICADA,
            radicado="FODEJAS-2026-00002",
        )

        self.solicitud3 = Solicitud.objects.create(
            convocatoria=self.convocatoria,
            aspirante=self.aspirante3,
            estado=Solicitud.Estado.VERIFICADA,
            radicado="FODEJAS-2026-00003",
        )

        # Create puntajes (scores) for each solicitud
        # Note: The model uses puntaje_academico, puntaje_excelencia
        # Solicitud 1: Highest score
        PuntajeTotal.objects.create(
            solicitud=self.solicitud1,
            puntaje_socioeconomico=30.00,
            puntaje_academico=45.00,
            puntaje_excelencia=20.00,
            puntaje_total=95.00,
        )

        # Solicitud 2: Medium score
        PuntajeTotal.objects.create(
            solicitud=self.solicitud2,
            puntaje_socioeconomico=25.00,
            puntaje_academico=40.00,
            puntaje_excelencia=15.00,
            puntaje_total=80.00,
        )

        # Solicitud 3: Lowest score
        PuntajeTotal.objects.create(
            solicitud=self.solicitud3,
            puntaje_socioeconomico=20.00,
            puntaje_academico=35.00,
            puntaje_excelencia=10.00,
            puntaje_total=65.00,
        )

        self.client = Client()

    def tearDown(self):
        """Clean up after tests."""
        # Delete in correct order to respect foreign key constraints
        # 1. ListadoDefinitivo (references Convocatoria and Acto)
        ListadoDefinitivo.objects.all().delete()
        # 2. Solicitud (references Convocatoria)
        Solicitud.objects.all().delete()
        # 3. ActoAdministrativo (references Convocatoria)
        ActoAdministrativo.objects.all().delete()
        # 4. Convocatoria
        Convocatory.objects.all().delete()
        # 5. SecuencialActo
        SecuencialActo.objects.all().delete()
        # 6. Users
        CustomUser.objects.filter(documento__startswith="TEST").delete()

    def test_01_flujo_scoring_obtener_ranking(self):
        """Step 1: Test scoring - obtener_ranking_final returns correct ordering."""
        # Get ranking from verified solicitudes with puntajes
        ranking = obtener_ranking_final(self.convocatoria)

        # Verify ranking is sorted by puntaje descending
        self.assertEqual(len(ranking), 3)

        # First should be highest score
        self.assertEqual(ranking[0]["radicado"], "FODEJAS-2026-00001")
        self.assertEqual(ranking[0]["puntaje"], 95.00)
        self.assertEqual(ranking[0]["rank"], 1)

        # Second should be medium score
        self.assertEqual(ranking[1]["radicado"], "FODEJAS-2026-00002")
        self.assertEqual(ranking[1]["puntaje"], 80.00)
        self.assertEqual(ranking[1]["rank"], 2)

        # Third should be lowest score
        self.assertEqual(ranking[2]["radicado"], "FODEJAS-2026-00003")
        self.assertEqual(ranking[2]["puntaje"], 65.00)
        self.assertEqual(ranking[2]["rank"], 3)

    def test_02_flujo_acto_administrativo_generar_numero(self):
        """Step 2: Test acto administrativo - generate sequential number."""
        # Generate first number
        numero1 = generar_numero_acto("resolucion")
        self.assertRegex(numero1, r"^FODEJAS-\d{4}-00001$")

        # Generate second number - should increment
        numero2 = generar_numero_acto("resolucion")
        self.assertRegex(numero2, r"^FODEJAS-\d{4}-00002$")

        # Create acto administrativo
        acto = ActoAdministrativo.objects.create(
            numero=numero2,
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion=timezone.now().date(),
            asunto="Resolución de resultados definitivos",
            resolutivo="Se aprueban los resultados definitivos de la convocatoria",
            convocatoria=self.convocatoria,
            estado=ActoAdministrativo.Estado.BORRADOR,
        )

        # Verify acto was created
        self.assertIsNotNone(acto.pk)
        self.assertEqual(acto.numero, numero2)
        self.assertEqual(acto.tipo, ActoAdministrativo.Tipo.RESOLUCION)
        self.assertEqual(acto.estado, ActoAdministrativo.Estado.BORRADOR)

    def test_03_flujo_listado_definitivo_crear(self):
        """Step 3: Test listado definitivo - create listing with ranking."""
        # First generate the acto
        numero = generar_numero_acto("resolucion")
        acto = ActoAdministrativo.objects.create(
            numero=numero,
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion=timezone.now().date(),
            asunto="Resolución de resultados definitivos",
            resolutivo="Se aprueban los resultados definitivos",
            convocatoria=self.convocatoria,
            estado=ActoAdministrativo.Estado.BORRADOR,
        )

        # Get ranking data
        ranking = obtener_ranking_final(self.convocatoria)

        # Create the listing
        listado = generar_listado_definitivo(self.convocatoria, acto, ranking)

        # Verify listing was created
        self.assertIsNotNone(listado.pk)
        self.assertEqual(listado.convocatoria, self.convocatoria)
        self.assertEqual(listado.acto, acto)
        self.assertEqual(len(listado.ranking), 3)

        # Verify ranking order in listing
        self.assertEqual(listado.ranking[0]["rank"], 1)
        self.assertEqual(listado.ranking[0]["puntaje"], 95.00)

        # Verify convocatoria state was updated
        self.convocatoria.refresh_from_db()
        self.assertEqual(
            self.convocatoria.estado,
            Convocatory.Estado.RESULTADOS_DEFINITIVOS
        )

    def test_04_flujo_publicacion_vista_publica(self):
        """Step 4: Test publicación - verify public view without PII."""
        # Create the full flow first
        numero = generar_numero_acto("resolucion")
        acto = ActoAdministrativo.objects.create(
            numero=numero,
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion=timezone.now().date(),
            asunto="Resolución de resultados definitivos",
            resolutivo="Se aprueban los resultados definitivos",
            convocatoria=self.convocatoria,
            estado=ActoAdministrativo.Estado.BORRADOR,
        )

        ranking = obtener_ranking_final(self.convocatoria)
        listado = generar_listado_definitivo(self.convocatoria, acto, ranking)

        # Access public view (no login required)
        url = reverse("convocatories:resultados_publicos", kwargs={"codigo": self.convocatoria.codigo})
        response = self.client.get(url)

        # Verify response is successful
        self.assertEqual(response.status_code, 200)

        # Verify context contains aggregate data but NOT PII
        context = response.context

        # Should have aggregate data
        self.assertEqual(context["total_beneficiarios"], 3)
        self.assertEqual(context["puntaje_maximo"], 95.00)
        self.assertEqual(context["puntaje_minimo"], 65.00)

        # Should have the acto
        self.assertEqual(context["acto"], acto)

        # Verify NO personal data in context
        # The ranking in public view should be sanitized
        if "listado" in context:
            # Check that we don't expose personal identifiers
            ranking_data = context["listado"].ranking
            for item in ranking_data:
                # No email, no full name, no identification numbers
                self.assertNotIn("email", str(item).lower())
                self.assertNotIn("identificacion", str(item).lower())

    def test_05_flujo_completo_e2e(self):
        """Complete E2E flow test - all steps together."""
        # Step 1: Get ranking
        ranking = obtener_ranking_final(self.convocatoria)
        self.assertEqual(len(ranking), 3)

        # Step 2: Generate acto number and create acto
        numero = generar_numero_acto("resolucion")
        acto = ActoAdministrativo.objects.create(
            numero=numero,
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion=timezone.now().date(),
            asunto="Resolución resultados definitivos",
            resolutivo="Se publican los resultados definitivos",
            convocatoria=self.convocatoria,
            estado=ActoAdministrativo.Estado.FIRMADO,
        )

        # Step 3: Create listing
        listado = generar_listado_definitivo(self.convocatoria, acto, ranking)
        self.assertIsNotNone(listado.pk)

        # Verify the listing exists and is linked correctly
        self.assertTrue(
            ListadoDefinitivo.objects.filter(
                convocatoria=self.convocatoria
            ).exists()
        )

        # Step 4: Verify public access works
        url = reverse("convocatories:resultados_publicos", kwargs={"codigo": self.convocatoria.codigo})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

        # Verify no PII in response content
        content = response.content.decode("utf-8")
        # Should not contain personal data
        self.assertNotIn("aspirante1@test.com", content)
        self.assertNotIn("aspirante2@test.com", content)
        self.assertNotIn("Juan Perez", content)
        self.assertNotIn("Maria Garcia", content)
