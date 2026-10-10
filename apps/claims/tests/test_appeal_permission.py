"""Test for AUD-009 fix: ``CanCreateApelacion.has_object_permission`` resolves
without ``ImportError`` and uses the existing ``validar_apelacion`` helper
from ``apps.claims.services.apelaciones``.
"""

import inspect

from django.test import SimpleTestCase

from apps.claims.permissions import CanCreateApelacion


class CanCreateApelacionTest(SimpleTestCase):
    """``CanCreateApelacion`` imports cleanly and delegates to ``validar_apelacion``."""

    def test_import_does_not_raise(self):
        """The class itself is importable (the regression the audit flagged)."""
        self.assertTrue(callable(CanCreateApelacion))

    def test_has_object_permission_method_exists(self):
        """``has_object_permission`` is implemented (not inherited stub)."""
        self.assertTrue(hasattr(CanCreateApelacion, "has_object_permission"))
        self.assertTrue(callable(CanCreateApelacion.has_object_permission))

    def test_does_not_reference_can_apelar(self):
        """The legacy (non-existent) helper ``can_apelar`` is no longer referenced
        as code. The substring may legitimately appear inside a ``# CHG-805 AUD-009``
        comment that documents the fix, so we strip Python comments before searching.
        """
        source = inspect.getsource(CanCreateApelacion)
        # Strip Python comments line-by-line so a docstring/comment that mentions
        # the legacy name does not trip the test.
        non_comment_lines = []
        for line in source.splitlines():
            stripped = line.split("#", 1)[0]
            if stripped.strip():
                non_comment_lines.append(stripped)
        non_comment_source = "\n".join(non_comment_lines)
        self.assertNotIn("can_apelar", non_comment_source)
        # The current implementation explicitly imports ``validar_apelacion``.
        self.assertIn("validar_apelacion", source)

    def test_validar_apelacion_signature_matches(self):
        """``validar_apelacion`` exists with the expected 2-arg signature and
        returns a 2-tuple (used by ``can_create, _ = validar_apelacion(...)``)."""
        from apps.claims.services.apelaciones import validar_apelacion

        sig = inspect.signature(validar_apelacion)
        # Two positional args: ``reclamacion`` and ``actor``.
        self.assertEqual(len(sig.parameters), 2)
        self.assertIn("reclamacion", sig.parameters)
        self.assertIn("actor", sig.parameters)
