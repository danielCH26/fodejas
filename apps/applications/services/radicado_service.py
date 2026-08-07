"""Service for generating radicado numbers."""
from django.db import transaction
from django.utils import timezone


def generar_radicado() -> str:
    """Generate a unique radicado in format FODEJAS-YYYY-NNNNN.

    Uses select_for_update to ensure atomic sequence generation.

    Returns:
        Radicado string in format FODEJAS-YYYY-NNNNN

    Example:
        FODEJAS-2026-00001
    """
    from apps.applications.models import RadicadoSecuencial

    anio = timezone.now().year

    with transaction.atomic():
        # Get or create the sequence for this year
        seq, created = RadicadoSecuencial.objects.select_for_update().get_or_create(
            anio=anio,
            defaults={"secuencia": 0},
        )

        # Increment sequence
        seq.secuencia += 1
        seq.save()

        # Format: FODEJAS-YYYY-NNNNN
        radicado = f"FODEJAS-{anio}-{seq.secuencia:05d}"

    return radicado
