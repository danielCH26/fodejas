#!/usr/bin/env python
"""
compile_mo.py — CHG-507 (Unit A)

Compiles all django.po files in locale/*/LC_MESSAGES/ to django.mo
using polib (pure-Python, no gettext required).

Usage:
    python scripts/compile_mo.py

Exit codes:
    0  — all locales compiled successfully
    1  — one or more .po files failed to compile or write

The polib .mo output is deterministic (same .po → same .mo bytes on
two consecutive runs). Verified by running twice and comparing MD5.
"""

from __future__ import annotations

import sys
from pathlib import Path

import polib


def compile_locale_po(po_path: Path) -> tuple[bool, str, int]:
    """
    Compile a single django.po file to django.mo.

    Returns:
        (success: bool, locale_name: str, entry_count: int)
    """
    try:
        po = polib.pofile(str(po_path))
    except Exception as exc:
        return False, po_path.parent.parent.name, 0

    mo_path = po_path.with_suffix(".mo")
    po.save_as_mofile(str(mo_path))

    # Count translated entries (msgid + non-empty msgstr)
    translated = sum(1 for e in po if e.msgstr and e.msgstr.strip())
    return True, po_path.parent.parent.name, translated


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    locale_root = repo_root / "locale"

    if not locale_root.exists():
        print(f"ERROR: locale directory not found at {locale_root}", file=sys.stderr)
        return 1

    po_files = list(locale_root.glob("*/LC_MESSAGES/django.po"))
    if not po_files:
        print(f"WARNING: No django.po files found under {locale_root}", file=sys.stderr)

    failures = []
    success_count = 0

    for po_path in sorted(po_files):
        ok, locale, count = compile_locale_po(po_path)
        mo_path = po_path.with_suffix(".mo")
        if ok:
            print(f"  OK  [{locale:8}] {po_path.name} -> {mo_path.name}  ({count} translated)")
            success_count += 1
        else:
            print(f"  FAIL[{locale:8}] {po_path}", file=sys.stderr)
            failures.append(str(po_path))

    print(f"\nCompiled {success_count}/{success_count + len(failures)} locale(s).")

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
