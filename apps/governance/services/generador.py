"""Generador de consecutivos para actos administrativos (CHG-207 + CHG-208)."""

from django.db import transaction
from django.utils import timezone


def generar_numero_acto(tipo: str) -> str:
    """
    Genera número de acto administrativo de forma thread-safe.

    Formato: ``FODEJAS-<TIPO>-YYYY-NNNNN`` donde ``<TIPO>`` es el
    prefijo de 4 caracteres del tipo (RESO, ACTA, MODI, CERT). Cada
    tipo tiene su propia secuencia anual independiente — así una
    Resolución y un Modificatorio del mismo año nunca colisionan en
    el campo ``numero`` único.

    Args:
        tipo: Tipo de acto (resolucion, acta, modificatorio, certificacion).

    Returns:
        Número de acto formateado, ej: ``"FODEJAS-RESO-2026-00001"``.

    Raises:
        ValueError: Si el tipo no es válido.
    """
    from apps.governance.models import SecuencialActo

    # Normalizar tipo
    tipo_normalizado = tipo.lower().strip()

    # Validar tipo
    tipos_validos = {
        "resolucion": "RESO",
        "acta": "ACTA",
        "modificatorio": "MODI",
        "certificacion": "CERT",
    }
    if tipo_normalizado not in tipos_validos:
        raise ValueError(f"Tipo de acto inválido: {tipo}")

    prefijo = tipos_validos[tipo_normalizado]
    anio = timezone.now().year

    with transaction.atomic():
        seq, created = SecuencialActo.objects.select_for_update().get_or_create(
            tipo=tipo_normalizado, anio=anio, defaults={"secuencia": 0}
        )
        seq.secuencia += 1
        seq.save()

    return f"FODEJAS-{prefijo}-{anio}-{seq.secuencia:05d}"
