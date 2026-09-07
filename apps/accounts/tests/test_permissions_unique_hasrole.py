"""Test for AUD-006 fix: ``apps.accounts.permissions.HasRole`` is defined
exactly once and accepts ``role_code`` as a constructor kwarg.
"""
import ast
import inspect
from pathlib import Path

from django.test import SimpleTestCase

from apps.accounts.permissions import HasRole


HASROLE_PATH = Path(__file__).resolve().parents[2] / "accounts" / "permissions.py"


class HasRoleUniquenessTest(SimpleTestCase):
    """``HasRole`` exists exactly once and exposes the constructor contract."""

    def test_has_role_accepts_role_code_kwarg(self):
        """The remaining ``HasRole`` class accepts ``role_code=...`` in ``__init__``."""
        instance = HasRole(role_code="R-ADMIN")
        self.assertEqual(instance.role_code, "R-ADMIN")

    def test_has_role_optional_role_code(self):
        """``role_code=None`` is the documented default (no role filter)."""
        instance = HasRole()
        self.assertIsNone(instance.role_code)

    def test_has_role_is_a_drf_permission(self):
        """``HasRole`` derives from DRF's ``BasePermission``."""
        from rest_framework.permissions import BasePermission

        self.assertTrue(issubclass(HasRole, BasePermission))

    def test_has_role_defined_exactly_once(self):
        """Only one ``class HasRole`` definition lives in ``permissions.py``."""
        source = HASROLE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)

        hasrole_classes = [
            node
            for node in tree.body
            if isinstance(node, ast.ClassDef) and node.name == "HasRole"
        ]
        self.assertEqual(
            len(hasrole_classes),
            1,
            "apps.accounts.permissions must declare exactly one ``class HasRole``",
        )

    def test_has_role_helper_call_signature_preserved(self):
        """Module-level helpers ``has_role`` / ``has_any_role`` accept a
        ``user`` argument (the equivalent of the deleted instance-method API)."""
        from apps.accounts.permissions import has_role, has_any_role, get_user_roles

        sig_has_role = inspect.signature(has_role)
        sig_has_any = inspect.signature(has_any_role)
        self.assertIn("user", sig_has_role.parameters)
        self.assertIn("user", sig_has_any.parameters)
        self.assertIn("user", inspect.signature(get_user_roles).parameters)
