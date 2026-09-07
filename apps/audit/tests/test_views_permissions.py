"""Permission tests for the audit API endpoints (CHG-801 / AUD-015).

The list/detail endpoints must require ``IsAuditViewer`` (R-ADMIN or
R-CONTROL). Unauthenticated clients are denied and R-ASPIRANTE is
denied.

We exercise the ``IsAuditViewer`` permission class directly against
an API request, which is exactly what the view does under the hood.
This avoids loading ``config.urls`` (which transitively imports
``django_prometheus.urls`` — not available in every setup) while
still testing the production permission contract.
"""
from __future__ import annotations

import uuid

import pytest
from rest_framework.test import APIRequestFactory

from apps.accounts.permissions import IsAuditViewer


@pytest.mark.django_db
class TestAuditApiPermissions:
    """``/api/audit/events/`` permission tightening (CHG-801 / AUD-015)."""

    def _request(self, user=None):
        factory = APIRequestFactory()
        request = factory.get("/api/audit/events/")
        request.user = user if user is not None else (
            type("_A", (), {"is_authenticated": False, "is_superuser": False, "is_staff": False})()
        )
        return request

    def test_anonymous_client_is_forbidden(self):
        request = self._request(user=None)
        permission = IsAuditViewer()
        assert permission.has_permission(request, view=None) is False

    def test_aspirante_role_is_forbidden(self, aspirante_user_with_role):
        request = self._request(user=aspirante_user_with_role)
        permission = IsAuditViewer()
        assert permission.has_permission(request, view=None) is False

    def test_admin_role_is_allowed(self, admin_user_with_role):
        request = self._request(user=admin_user_with_role)
        permission = IsAuditViewer()
        assert permission.has_permission(request, view=None) is True

    def test_superuser_is_allowed(self, admin_user):
        request = self._request(user=admin_user)
        permission = IsAuditViewer()
        result = permission.has_permission(request, view=None)
        assert result is True, (
            f"superuser denied: is_authenticated={admin_user.is_authenticated} "
            f"is_superuser={admin_user.is_superuser} is_staff={admin_user.is_staff} "
            f"is_active={admin_user.is_active}"
        )

    def test_view_permission_classes_use_isauditviewer(self):
        """Source-level check: ``AuditEventListView`` and the DRF
        ``AuditEventDetailView`` must declare ``[IsAuditViewer]`` as
        their permission classes (CHG-801 / AUD-015).

        We parse the source rather than introspect the class
        because ``apps.audit.views`` defines two classes with the
        name ``AuditEventDetailView`` (a DRF view and an HTML view)
        and the HTML one shadows the DRF one in the module
        namespace. Parsing the source avoids that pitfall.
        """
        import ast
        import importlib.util

        source_path = importlib.util.find_spec("apps.audit.views").origin
        with open(source_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())

        # Collect every ClassDef in document order with its lineno
        # so we can pick the *first* definition of each name (the
        # DRF one is defined before the HTML one).
        class_defs: list[tuple[str, int, ast.ClassDef]] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                class_defs.append((node.name, node.lineno, node))

        def _permission_classes_for(class_name: str) -> list[str] | None:
            matches = [c for n, _, c in class_defs if n == class_name]
            if not matches:
                return None
            cls = matches[0]  # first definition is the DRF one
            for stmt in cls.body:
                if (
                    isinstance(stmt, ast.Assign)
                    and len(stmt.targets) == 1
                    and isinstance(stmt.targets[0], ast.Name)
                    and stmt.targets[0].id == "permission_classes"
                ):
                    value = stmt.value
                    if isinstance(value, ast.List):
                        elements: list[str] = []
                        for elt in value.elts:
                            if isinstance(elt, ast.Name):
                                elements.append(elt.id)
                            elif isinstance(elt, ast.Attribute):
                                elements.append(ast.unparse(elt))
                        return elements
            return []

        list_perms = _permission_classes_for("AuditEventListView")
        detail_perms = _permission_classes_for("AuditEventDetailView")
        assert list_perms is not None, "AuditEventListView not found in views.py"
        assert detail_perms is not None, "AuditEventDetailView not found in views.py"

        assert "IsAuditViewer" in list_perms, (
            f"AuditEventListView permission_classes={list_perms}; "
            "expected IsAuditViewer (CHG-801 / AUD-015)."
        )
        assert "IsAuditViewer" in detail_perms, (
            f"AuditEventDetailView permission_classes={detail_perms}; "
            "expected IsAuditViewer (CHG-801 / AUD-015)."
        )
        # ``IsAuthenticated`` alone would let any logged-in user
        # read the log — explicitly forbidden by CHG-801 / AUD-015.
        assert "IsAuthenticated" not in list_perms, (
            f"AuditEventListView still permits IsAuthenticated "
            f"({list_perms}); aspirants could read the log."
        )
        assert "IsAuthenticated" not in detail_perms, (
            f"AuditEventDetailView still permits IsAuthenticated "
            f"({detail_perms}); aspirants could read the log."
        )