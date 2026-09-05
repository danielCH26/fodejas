"""Tests for generador service (CHG-207)."""
import pytest
from django.test import TestCase
from django.utils import timezone

from apps.governance.models import SecuencialActo
from apps.governance.services.generador import generar_numero_acto


class TestGeneradorNumeroActo(TestCase):
    """Tests for generar_numero_acto function."""

    def test_generar_numero_formato_correcto(self):
        """Test that generated number has correct format FODEJAS-YYYY-NNNNN."""
        numero = generar_numero_acto("resolucion")

        # Should match format FODEJAS-YYYY-NNNNN
        self.assertRegex(numero, r"^FODEJAS-\d{4}-\d{5}$")

    def test_generar_numero_incrementa_secuencia(self):
        """Test that consecutive calls increment the sequence."""
        numero1 = generar_numero_acto("resolucion")
        numero2 = generar_numero_acto("resolucion")

        # Extract sequence numbers
        seq1 = int(numero1.split("-")[-1])
        seq2 = int(numero2.split("-")[-1])

        self.assertEqual(seq2, seq1 + 1)

    def test_generar_numero_diferentes_tipos(self):
        """Test that different types have independent sequences."""
        from django.utils import timezone
        import threading

        # Limpiar secuenciales de prueba
        anio = timezone.now().year
        SecuencialActo.objects.filter(tipo="resolucion", anio=anio).delete()
        SecuencialActo.objects.filter(tipo="acta", anio=anio).delete()

        # Generar números para cada tipo
        numero_resolucion_1 = generar_numero_acto("resolucion")
        numero_acta_1 = generar_numero_acto("acta")

        # Verificar que cada tipo tiene su propio secuencial
        # Ambos deben empezar en 00001
        self.assertTrue(numero_resolucion_1.endswith("-00001"))
        self.assertTrue(numero_acta_1.endswith("-00001"))

        # Generar segundo número para cada tipo
        numero_resolucion_2 = generar_numero_acto("resolucion")
        numero_acta_2 = generar_numero_acto("acta")

        # Verificar que el secuencial de cada tipo avanza independientemente
        seq_resolucion = int(numero_resolucion_2.split("-")[-1])
        seq_acta = int(numero_acta_2.split("-")[-1])

        # Resolucion debe ser 00002, Acta debe ser 00002
        self.assertEqual(seq_resolucion, 2)
        self.assertEqual(seq_acta, 2)

        # Verificar en la base de datos que hay registros separados
        self.assertTrue(SecuencialActo.objects.filter(tipo="resolucion", anio=anio).exists())
        self.assertTrue(SecuencialActo.objects.filter(tipo="acta", anio=anio).exists())

    def test_generar_numero_tipo_invalido(self):
        """Test that invalid type raises ValueError."""
        with self.assertRaises(ValueError) as context:
            generar_numero_acto("tipo_invalido")

        self.assertIn("inválido", str(context.exception))

    def test_generar_numero_thread_safe(self):
        """Test that concurrent calls don't cause race conditions."""
        import threading

        resultados = []

        def generar():
            numero = generar_numero_acto("resolucion")
            resultados.append(numero)

        # Run multiple threads
        threads = [threading.Thread(target=generar) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All results should be unique
        self.assertEqual(len(resultados), len(set(resultados)))

    def test_secuencial_acto_se_crea(self):
        """Test that SecuencialActo is created if not exists."""
        anio = timezone.now().year
        tipo = "resolucion"

        # Delete any existing
        SecuencialActo.objects.filter(tipo=tipo, anio=anio).delete()

        # Generate first number
        numero = generar_numero_acto(tipo)

        # Should have created the secuencial
        seq = SecuencialActo.objects.get(tipo=tipo, anio=anio)
        self.assertEqual(seq.secuencia, 1)
