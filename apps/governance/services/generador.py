"""Generador de consecutivos para actos administrativos (CHG-207)."""
from django.db import transaction
from django.utils import timezone


def generar_numero_acto(tipo: str) -> str:
    """
    Genera número de acto administrativo de forma thread-safe.
    
    Formato: FODEJAS-YYYY-NNNNN
    
    Args:
        tipo: Tipo de acto (resolucion, acta, etc.)
    
    Returns:
        Número de acto formateado, ej: "FODEJAS-2026-00001"
    
    Raises:
        ValueError: Si el tipo no es válido
    """
    from apps.governance.models import SecuencialActo

    # Normalizar tipo
    tipo_normalizado = tipo.lower().strip()

    # Validar tipo
    tipos_validos = ["resolucion", "acta", "modificatorio", "certificacion"]
    if tipo_normalizado not in tipos_validos:
        raise ValueError(f"Tipo de acto inválido: {tipo}")

    anio = timezone.now().year

    with transaction.atomic():
        seq, created = SecuencialActo.objects.select_for_update().get_or_create(
            tipo=tipo_normalizado,
            anio=anio,
            defaults={"secuencia": 0}
        )
        seq.secuencia += 1
        seq.save()

    return f"FODEJAS-{anio}-{seq.secuencia:05d}"
