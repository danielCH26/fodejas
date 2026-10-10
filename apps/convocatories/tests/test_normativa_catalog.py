"""Test for AUD-011 fix: no entry of ``apps.convocatories.domain.normativa.NORMATIVA``
carries the literal placeholder ``Art. ...`` in its ``articulo`` field.
"""

from django.test import SimpleTestCase

from apps.convocatories.domain.normativa import NORMATIVA


class NormativaCatalogTest(SimpleTestCase):
    """No ``Art. ...`` placeholder remains in the catalog."""

    def test_no_art_placeholder_entries(self):
        """Every ``articulo`` string is concrete (no ``Art. ...`` substrings)."""
        offenders = []
        for key, entry in NORMATIVA.items():
            articulo = entry.get("articulo", "")
            if "Art. ..." in articulo:
                offenders.append((key, articulo))
        self.assertEqual(
            offenders,
            [],
            f"NORMATIVA keys still use the placeholder: {offenders}",
        )

    def test_articulos_non_empty(self):
        """Every entry has a non-empty ``articulo`` string (AGENTS.md §6 regla 4)."""
        offenders = []
        for key, entry in NORMATIVA.items():
            articulo = (entry.get("articulo") or "").strip()
            if not articulo:
                offenders.append(key)
        self.assertEqual(offenders, [], f"Empty articulo entries: {offenders}")

    def test_expected_entries_have_citations(self):
        """The four plazo entries declared by CHG-805 now cite a concrete decree."""
        expected_citations = {
            "beneficio_5_semestres": "Decreto 0372/2025",
            "beneficio_10_semestres": "Decreto 0372/2025",
            "tesoreria_5_dias": "Decreto 0072/2026",
            "exoneracion_30_dias": "Decreto 0372/2025",
        }
        for key, expected in expected_citations.items():
            self.assertIn(key, NORMATIVA, f"{key} missing from NORMATIVA")
            self.assertIn(expected, NORMATIVA[key]["articulo"])
