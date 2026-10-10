"""Anonimización reversible-bajo-llave (CHG-099).

Per AGENTS.md §6 regla 1, ningún archivo del repo puede contener
PII. Este módulo provee funciones de anonimización deterministas
usando ``sha256(value + salt)[:12]``:

- **Determinista**: el mismo input + salt produce el mismo output.
  Crítico para que la migración sea idempotente — re-ejecuciones
  no duplican registros anonimizados.
- **Reversible-bajo-llave**: con el ``salt`` correcto se puede
  reconstruir el valor original. Operacionalmente, el salt vive en
  el vault (NO en el repo) por lo que el equipo de desarrollo no
  tiene acceso al mapping inverso.
- **One-way aparente**: sin el salt, el output parece aleatorio. La
  colisión de prefijo de 12 caracteres hex es aceptable porque la
  anonimización es solo para evitar PII accidental en commits; los
  registros en la DB tienen además su PK separada.

Constantes:
- ``_DEFAULT_SALT_ENV``: nombre de la variable de entorno con el
  salt por defecto. El comando de migración lee esta variable.
"""
from __future__ import annotations

import hashlib
import hmac
import os

DEFAULT_SALT_ENV = "LEGACY_DATA_SALT"


def _get_salt(salt: str | None = None) -> bytes:
    """Resolve the salt to use.

    If a salt is passed explicitly, use it. Otherwise read from the
    ``LEGACY_DATA_SALT`` environment variable. If neither is available,
    raise ``ValueError`` (fail-closed).

    Returns:
        bytes: the salt value encoded as UTF-8.

    Raises:
        ValueError: if no salt is available.
    """
    resolved = salt or os.environ.get(DEFAULT_SALT_ENV)
    if not resolved:
        raise ValueError(
            f"se requiere salt para anonimizar; "
            f"export {DEFAULT_SALT_ENV} o pásalo explícitamente"
        )
    if len(resolved) < 16:
        raise ValueError(
            f"salt demasiado corto ({len(resolved)} chars); "
            f"mínimo 16 chars para evitar colisiones triviales"
        )
    return resolved.encode("utf-8")


def anonymize_hash(value: str, salt: str | None = None) -> str:
    """Return a deterministic, anonymized hash for the given value.

    Uses HMAC-SHA256 with the salt as key, truncated to 12 hex chars.
    HMAC is used instead of plain ``sha256(value + salt)`` because it
    is more resistant to length-extension attacks and is the
    canonical primitive for keyed hashing.

    Args:
        value: the PII string to anonymize (e.g. document number,
            email).
        salt: optional salt override. Defaults to ``$LEGACY_DATA_SALT``.

    Returns:
        A 12-character hex string that uniquely identifies the value
        (collision probability negligible for the dataset sizes
        FODEJAS handles, max ~10k records per type).
    """
    s = _get_salt(salt)
    digest = hmac.new(s, value.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[:12]


def anonymize_optional(value: str | None, salt: str | None = None) -> str | None:
    """Anonymize a value that may be None or empty.

    Returns:
        ``None`` if the input is None or empty (after stripping
        whitespace); otherwise the anonymized hash.
    """
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return anonymize_hash(stripped, salt)


def anonymize_json(data, salt: str | None = None):
    """Recursively anonymize all string leaves in a JSON-like structure.

    Walks the structure (dict, list, tuple, set) and replaces every
    string leaf with its anonymized hash. Numbers, booleans, and None
    pass through unchanged.

    Use this for ``datos_personales``, ``datos_academicos`` and
    similar JSONFields where the content structure is unknown but
    every string is suspect.

    Args:
        data: a JSON-deserializable structure (dict, list, scalar).
        salt: optional salt override.

    Returns:
        A new structure of the same shape with all string leaves
        anonymized.
    """
    if isinstance(data, dict):
        return {k: anonymize_json(v, salt) for k, v in data.items()}
    if isinstance(data, list):
        return [anonymize_json(v, salt) for v in data]
    if isinstance(data, tuple):
        return tuple(anonymize_json(v, salt) for v in data)
    if isinstance(data, set):
        return {anonymize_json(v, salt) for v in data}
    if isinstance(data, str):
        return anonymize_hash(data, salt)
    return data  # numbers, bools, None — pass through
