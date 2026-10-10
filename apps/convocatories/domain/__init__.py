"""Domain layer for convocatories app."""

from .transitions import (
    TRANSICIONES_PERMITIDAS,
    Estado,
    get_estado_display,
    get_transiciones_disponibles,
    is_active,
    is_terminal,
    transicionar,
    validar_transicion,
)

__all__ = [
    "Estado",
    "TRANSICIONES_PERMITIDAS",
    "get_estado_display",
    "get_transiciones_disponibles",
    "is_active",
    "is_terminal",
    "transicionar",
    "validar_transicion",
]
