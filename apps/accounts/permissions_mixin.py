"""Permission mixin for all views in FODEJAS Django project."""

from django.contrib import messages
from django.shortcuts import redirect


class PermissionMixin:
    """Mixin that provides permission context variables for templates."""

    def get_context_data(self, **kwargs):
        """Add permission context variables to all views."""
        context = super().get_context_data(**kwargs)
        request = self.request
        user = request.user

        # Check various role-based permissions
        context["can_manage"] = self._has_manage_permission(user)
        context["can_apply"] = self._has_role(user, "R-ASPIRANTE")
        context["can_review"] = self._has_role(user, "R-REVISOR")
        context["can_score"] = self._has_role(user, "R-COMITE")
        context["can_claim"] = self._has_role(user, "R-ASPIRANTE")  # Only aspirants can claim
        context["can_admin_users"] = self._has_role(user, "R-ADMIN")
        context["can_admin_roles"] = self._has_role(user, "R-ADMIN")
        context["can_junta"] = self._has_role(user, "R-JUNTA")
        context["can_ofijur"] = self._has_role(user, "R-OFIJUR")
        context["can_coordinator"] = self._has_role(user, "R-COORDINADOR")
        context["can_treasurer"] = self._has_role(user, "R-TESORERO")

        # For convenience
        context["is_admin"] = context["can_manage"]
        context["is_aspirant"] = context["can_apply"]
        context["is_reviewer"] = context["can_review"]
        context["is_scorer"] = context["can_score"]

        return context

    def _has_manage_permission(self, user):
        """Check if user can manage (admin/coordinator/superuser)."""
        if not user.is_authenticated:
            return False

        # Check for admin role
        has_admin = user.user_roles.filter(role__code="R-ADMIN").exists()

        # Check for coordinator role
        has_coord = user.user_roles.filter(role__code="R-COORDINADOR").exists()

        # Check for superuser/staff
        is_superuser = user.is_superuser or user.is_staff

        return has_admin or has_coord or is_superuser

    def _has_role(self, user, role_code):
        """Check if user has a specific role."""
        if not user.is_authenticated:
            return False

        return user.user_roles.filter(role__code=role_code).exists()

    def _has_any_role(self, user, role_codes):
        """Check if user has any of the specified roles."""
        if not user.is_authenticated:
            return False

        return user.user_roles.filter(role__code__in=role_codes).exists()


class AdminPermissionMixin(PermissionMixin):
    """Mixin for admin-only views."""

    admin_roles = ["R-ADMIN", "R-COORDINADOR"]

    def dispatch(self, request, *args, **kwargs):
        """Check if user has admin permissions."""
        if not self._has_any_role(request.user, self.admin_roles) and not request.user.is_superuser:
            messages.error(request, "No tienes permisos para acceder a esta sección.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)


class ReviewerPermissionMixin(PermissionMixin):
    """Mixin for reviewer-only views."""

    def dispatch(self, request, *args, **kwargs):
        """Check if user has reviewer permissions."""
        if not self._has_role(request.user, "R-REVISOR") and not request.user.is_superuser:
            messages.error(request, "Solo revisores pueden acceder a esta sección.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)


class CommitteePermissionMixin(PermissionMixin):
    """Mixin for committee (scoring) views."""

    def dispatch(self, request, *args, **kwargs):
        """Check if user has committee permissions."""
        if not self._has_role(request.user, "R-COMITE") and not request.user.is_superuser:
            messages.error(request, "Solo miembros del comité pueden acceder a esta sección.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)


class JuntaPermissionMixin(PermissionMixin):
    """Mixin for junta (claims) views."""

    def dispatch(self, request, *args, **kwargs):
        """Check if user has junta permissions."""
        if not self._has_role(request.user, "R-JUNTA") and not request.user.is_superuser:
            messages.error(request, "Solo miembros de la junta pueden acceder a esta sección.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)


class OfijurPermissionMixin(PermissionMixin):
    """Mixin for OFIJUR (appeals) views."""

    def dispatch(self, request, *args, **kwargs):
        """Check if user has OFIJUR permissions."""
        if not self._has_role(request.user, "R-OFIJUR") and not request.user.is_superuser:
            messages.error(request, "Solo OFIJUR puede acceder a esta sección.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)
