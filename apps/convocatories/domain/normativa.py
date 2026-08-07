"""Normative references for convocatory rules.

References to legal articles from Ordenanzas and Decretos that govern
the convocatoria configuration rules.
"""

# Norma keys referenced in configuration
NORMATIVA = {
    # Plazos norms by nivel (Art. 16 Decreto 0372/2025)
    "plazo_tecnico": {
        "articulo": "Art. 16 Decreto 0372/2025",
        "descripcion": "Plazo para programas técnicos: 3 años",
        "meses": 36,
    },
    "plazo_tecnologico": {
        "articulo": "Art. 16 Decreto 0372/2025",
        "descripcion": "Plazo para programas tecnológicos: 4 años",
        "meses": 48,
    },
    "plazo_pregrado": {
        "articulo": "Art. 16 Decreto 0372/2025",
        "descripcion": "Plazo para pregrado: 6 años",
        "meses": 72,
    },
    "plazo_especializacion": {
        "articulo": "Art. 16 Decreto 0372/2025",
        "descripcion": "Plazo para especializaciones: 2 años",
        "meses": 24,
    },
    "plazo_maestria": {
        "articulo": "Art. 16 Decreto 0372/2025",
        "descripcion": "Plazo para maestrías: 2 años",
        "meses": 24,
    },
    "plazo_doctorado": {
        "articulo": "Art. 16 Decreto 0372/2025",
        "descripcion": "Plazo para doctorados: 5 años",
        "meses": 60,
    },
    # Beneficio duration (Art. ...)
    "beneficio_5_semestres": {
        "articulo": "Art. ... Decreto 0372/2025",
        "descripcion": "Beneficio educativo: 5 semestres",
        "semestres": 5,
    },
    "beneficio_10_semestres": {
        "articulo": "Art. ... Decreto 0372/2025",
        "descripcion": "Beneficio educativo: 10 semestres",
        "semestres": 10,
    },
    # Providencia references (Art. 11.5)
    "providencia_isla": {
        "articulo": "Art. 5 Ordenanza 007/2025",
        "descripcion": "Providencia es territorio insular especial",
        "codigo": "PROVIDENCIA",
    },
    # Tesorería payment window
    "tesoreria_5_dias": {
        "articulo": "Art. ... Decreto 0372/2025",
        "descripcion": "Tesorería ejecuta pago en 5 días hábiles",
        "dias": 5,
    },
    # Exoneration window
    "exoneracion_30_dias": {
        "articulo": "Art. ... Decreto 0372/2025",
        "descripcion": "Exoneración resuelta en 30 días calendario",
        "dias": 30,
    },
}


def get_normativa(key: str) -> dict | None:
    """Get normativa reference by key."""
    return NORMATIVA.get(key)


def list_normativa_keys() -> list[str]:
    """List all available normativa keys."""
    return list(NORMATIVA.keys())
