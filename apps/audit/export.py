"""Audit export service (CHG-505 / CAP-028).

Provides streaming CSV and JSONL export of the audit log, with a
two-pass SHA-256 integrity hash computed BEFORE streaming begins so
the ``X-Audit-Export-SHA256`` header is deterministic and matches the
exact body served.

Design notes
------------
Two passes over the DB are acceptable here (spec §E: "pass 1 iterate rows
→ update hasher + count; pass 2 iterate again for streaming").  Both passes
produce byte-identical content because row generation is deterministic: the
timestamp lives on the stored event (not injected mid-stream), entity_id is
stored as UUID, and changes are serialized with the exact same ``json.dumps``
recipe used by ``services.calculate_hash()``.

The first pass materialises rows in memory only as hex-digest chunks
(16 KiB each) — not as complete serialised strings — so the peak
working-set is bounded by the DB result-set cursor, not the full export.
Streaming then re-iterates the same queryset with ``.iterator()`` so the
second pass never holds more than one row at a time.

Hash algorithm for ``changes_str`` (mirrors
``apps.audit.services.calculate_hash``):
  - None  → literal string "null"
  - dict  → ``json.dumps(changes, sort_keys=True, default=str)``
  - No custom separators; ``default=str`` handles UUID / datetime.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from typing import TYPE_CHECKING, Iterator

if TYPE_CHECKING:
    from django.db.models.query import QuerySet

# Exact column whitelist — no PII (actor.email, actor.username) per
# project.md §13.2 / Ley 1581/2012.  13 columns covered by the hash chain.
AUDIT_EXPORT_COLUMNS = (
    "id",
    "timestamp",
    "actor_id",
    "actor_is_system",
    "action",
    "entity",
    "entity_id",
    "changes",
    "ip_address",
    "user_agent",
    "module",
    "previous_hash",
    "current_hash",
)


def _serialize_changes(changes) -> str:
    """Return the exact changes_str used by services.calculate_hash."""
    if changes is None:
        return "null"
    return json.dumps(changes, sort_keys=True, default=str)


def build_export_row(event) -> dict:
    """Return a dict mapping AUDIT_EXPORT_COLUMNS to serialised values.

    ``actor_is_system`` is inferred from the ``actor`` FK being NULL,
    which is the sentinel set by ``services.log_audit_event`` for
    system-origin events (CHG-801 / AUD-002).
    """
    return {
        "id": str(event.id),
        "timestamp": event.timestamp.isoformat(),
        "actor_id": event.actor_id if event.actor_id is not None else "",
        "actor_is_system": event.actor is None,
        "action": event.action,
        "entity": event.entity,
        "entity_id": str(event.entity_id),
        "changes": _serialize_changes(event.changes),
        "ip_address": event.ip_address or "",
        "user_agent": event.user_agent or "",
        "module": event.module or "",
        "previous_hash": event.previous_hash,
        "current_hash": event.current_hash,
    }


def iter_csv(queryset: "QuerySet") -> Iterator[bytes]:
    """Yield CSV lines (header + data rows) from a queryset.

    Uses ``.iterator()`` so only one row is held in memory at a time.
    """
    header_line = (",".join(AUDIT_EXPORT_COLUMNS) + "\n").encode("utf-8")
    yield header_line

    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=AUDIT_EXPORT_COLUMNS,
        extrasaction="ignore",
        lineterminator="\n",
    )
    for event in queryset.iterator():
        writer.writerow(build_export_row(event))
        yield buffer.getvalue().encode("utf-8")
        buffer.seek(0)
        buffer.truncate(0)


def iter_jsonl(queryset: "QuerySet") -> Iterator[bytes]:
    """Yield JSONL lines (one JSON object per event) from a queryset.

    Uses ``.iterator()`` so only one row is held in memory at a time.
    """
    for event in queryset.iterator():
        row = build_export_row(event)
        line = json.dumps(row, sort_keys=True, default=str) + "\n"
        yield line.encode("utf-8")


def iter_export_rows(queryset: "QuerySet") -> Iterator[dict]:
    """Yield serialised export rows (one dict per event) over a queryset.

    Generator version for callers that need structured rows rather
    than formatted bytes.
    """
    for event in queryset.iterator():
        yield build_export_row(event)


def _hash_bytes(hasher, data: bytes, chunk: bytearray, view: memoryview) -> None:
    """Feed bytes to hasher in 16 KiB chunks."""
    pos = 0
    while pos < len(data):
        n = min(len(data) - pos, len(view))
        view[:n] = data[pos : pos + n]
        hasher.update(view[:n])
        pos += n


def compute_payload_sha256(queryset: "QuerySet", fmt: str):
    """Hash all events in the queryset and return (hex_digest, event_count).

    This is the FIRST pass.  It iterates the queryset and feeds
    16 KiB chunks to the hasher so peak memory is bounded by the DB
    cursor, not the full export payload.

    Returns (sha256_hex, event_count).  The queryset is consumed once;
    callers MUST call the streaming generator separately for the second
    pass (identical rows, identical serialisation).
    """
    hasher = hashlib.sha256()
    count = 0
    chunk = bytearray(16 * 1024)
    view = memoryview(chunk)

    # Hash the header line first (matches the _gen() in views.py).
    if fmt == "csv":
        header_bytes = (",".join(AUDIT_EXPORT_COLUMNS) + "\n").encode("utf-8")
    else:
        header_bytes = b""
    _hash_bytes(hasher, header_bytes, chunk, view)

    for event in queryset.iterator():
        row = build_export_row(event)
        if fmt == "csv":
            line_buf = io.StringIO()
            writer = csv.DictWriter(
                line_buf,
                fieldnames=AUDIT_EXPORT_COLUMNS,
                extrasaction="ignore",
                lineterminator="\n",
            )
            writer.writerow(row)
            raw = line_buf.getvalue()
        else:
            raw = json.dumps(row, sort_keys=True, default=str) + "\n"
        _hash_bytes(hasher, raw.encode("utf-8"), chunk, view)
        count += 1

    return hasher.hexdigest(), count
