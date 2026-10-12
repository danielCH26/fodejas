"""Custom permission classes based on UserRole system."""

from django.db import models
from rest_framework import permissions
from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """
    Verifies that the user has the role R-ADMIN.

    Different from IsAdminUser:
    - IsAdminUser checks is_staff or is_superuser
    - IsAdminRole checks user_roles with role__code='R-ADMIN'
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.user_roles.filter(role__code="R-ADMIN").exists()


# CHG-805 AUD-006: the legacy duplicate ``HasRole`` that exposed
# ``has_role``/``has_any_role``/``has_all_roles`` as instance methods
# has been removed. Those helpers now live as module-level functions
# further down this file (``has_role``, ``has_any_role``,
# ``get_user_roles``, ``is_internal_user``, ``is_external_user``)
# with a consistent signature ``(user, role_code)`` /
# ``(user, [role_codes])``.


class HasRole(permissions.BasePermission):
    """
    Permission class that checks if user has a specific role.

    Usage:
        permission_classes = [HasRole('R-ADMIN')]
    """

    def __init__(self, role_code=None):
        self.role_code = role_code

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        if self.role_code is None:
            # If no role specified, just check if user has any role
            return request.user.user_roles.exists()

        return request.user.user_roles.filter(role__code=self.role_code).exists()


class HasAnyRole(permissions.BasePermission):
    """
    Permission class that checks if user has any of the specified roles.

    Usage:
        permission_classes = [HasAnyRole(['R-ADMIN', 'R-COMITE'])]
    """

    def __init__(self, role_codes):
        self.role_codes = role_codes if isinstance(role_codes, list) else [role_codes]

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.user_roles.filter(role__code__in=self.role_codes).exists()


class HasAllRoles(permissions.BasePermission):
    """
    Permission class that checks if user has all of the specified roles.

    Usage:
        permission_classes = [HasAllRoles(['R-COMITE', 'R-TESOR'])]
    """

    def __init__(self, role_codes):
        self.role_codes = role_codes if isinstance(role_codes, list) else [role_codes]

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        user_roles = set(request.user.user_roles.values_list("role__code", flat=True))
        return all(rc in user_roles for rc in self.role_codes)


class IsAdminOrHasRole(permissions.BasePermission):
    """
    Permission that allows admin users OR users with specific role.

    Usage:
        permission_classes = [IsAdminOrHasRole('R-REVISOR')]
    """

    def __init__(self, role_code=None):
        self.role_code = role_code

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Superusers and staff have full access
        if request.user.is_superuser or request.user.is_staff:
            return True

        if self.role_code is None:
            return request.user.user_roles.exists()

        return request.user.user_roles.filter(role__code=self.role_code).exists()


class HasRoleForConvocation(permissions.BasePermission):
    """
    Permission that checks if user has role for a specific convocation.

    Usage:
        permission_classes = [HasRoleForConvocation('R-REVISOR')]

    The convocation_id is read from view.kwargs or request.query_params.
    """

    def __init__(self, role_code):
        self.role_code = role_code

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        # Admin users bypass this check
        if request.user.is_superuser or request.user.is_staff:
            return True

        # Get convocation_id from various sources
        convocation_id = (
            view.kwargs.get("convocation_id")
            or view.kwargs.get("pk")
            or request.query_params.get("convocation_id")
        )

        if convocation_id is None:
            # No convocation specified - check for global role
            return request.user.user_roles.filter(
                role__code=self.role_code, convocation_scope_id__isnull=True
            ).exists()

        # Check for role in this convocation OR global role
        return (
            request.user.user_roles.filter(role__code=self.role_code)
            .filter(
                models.Q(convocation_scope_id=convocation_id)
                | models.Q(convocation_scope_id__isnull=True)
            )
            .exists()
        )


# Helper functions for common role checks
def has_role(user, role_code):
    """Check if user has a specific role."""
    if not user or not user.is_authenticated:
        return False
    return user.user_roles.filter(role__code=role_code).exists()


def has_any_role(user, role_codes):
    """Check if user has any of the specified roles."""
    if not user or not user.is_authenticated:
        return False
    return user.user_roles.filter(role__code__in=role_codes).exists()


def get_user_roles(user):
    """Get list of role codes for a user."""
    if not user or not user.is_authenticated:
        return []
    return list(user.user_roles.values_list("role__code", flat=True))


def is_internal_user(user):
    """Check if user is internal (staff or has internal role)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return True
    return user.user_roles.filter(role__type="interno").exists()


def is_external_user(user):
    """Check if user is external (no staff, external role only)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_staff or user.is_superuser:
        return False
    return user.user_roles.filter(role__type="externo").exists()


# === Audit Permissions ===


class IsAuditViewer(permissions.BasePermission):
    """
    Permission that allows R-ADMIN or R-CONTROL to view audit events.

    Usage:
        permission_classes = [IsAuditViewer]
    """

    AUDIT_VIEWER_ROLES = ["R-ADMIN", "R-CONTROL"]

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Superusers have full access
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.user_roles.filter(role__code__in=self.AUDIT_VIEWER_ROLES).exists()


class IsAuditAdmin(permissions.BasePermission):
    """
    Permission that allows only R-ADMIN to access audit administration.

    Usage:
        permission_classes = [IsAuditAdmin]
    """

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Superusers have full access
        if request.user.is_superuser:
            return True
        return request.user.user_roles.filter(role__code="R-ADMIN").exists()


# CHG-505 CAP-028 — Export permission for external audit ente.
# DRF re-instantiates permission classes per request, so role lists
# MUST be class-level attributes (not captured in __init__ closures).


class IsAuditExporter(permissions.BasePermission):
    """
    Permission that allows R-ADMIN, R-CONTROL, or R-AUDITOR to export
    the full audit log to CSV / JSONL (CAP-028).

    Usage:
        permission_classes = [IsAuditExporter]
    """

    AUDIT_EXPORT_ROLES = ["R-ADMIN", "R-CONTROL", "R-AUDITOR"]

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        # Superusers and staff have full access
        if request.user.is_superuser or request.user.is_staff:
            return True
        return request.user.user_roles.filter(
            role__code__in=self.AUDIT_EXPORT_ROLES
        ).exists()
