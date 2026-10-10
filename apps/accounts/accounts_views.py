"""Views for accounts app."""

from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView as BaseLoginView,
)
from django.contrib.auth.views import (
    LogoutView as BaseLogoutView,
)
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from rest_framework import permissions
from rest_framework.views import APIView

from .forms import (
    FodejasLoginForm,
    FodejasPasswordResetForm,
    FodejasRegistrationForm,
    FodejasSetPasswordForm,
)
from .models import Role, UserRole
from .permissions_mixin import PermissionMixin

User = get_user_model()


class LoginView(BaseLoginView):
    """Login view returning JWT tokens and user role metadata."""

    form_class = FodejasLoginForm
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        """Handle successful login."""
        user = form.get_user()

        # Update last activity
        user.last_activity = timezone.now()
        user.save(update_fields=["last_activity"])

        # Get user roles
        user_roles = UserRole.objects.filter(user=user).select_related("role")

        roles_data = []
        for ur in user_roles:
            roles_data.append(
                {
                    "code": ur.role.code,
                    "name": ur.role.name,
                    "type": ur.role.type,
                    "convocation": ur.convocation_scope_id,
                }
            )

        # If AJAX request, return JSON with tokens
        if self.request.headers.get("HX-Request"):
            # For HTMX requests, just return success
            return render(
                self.request,
                "accounts/partials/login_success.html",
                {
                    "user": user,
                    "roles": roles_data,
                },
            )

        # For regular form submission, redirect to dashboard
        login(self.request, user)
        return redirect("accounts:dashboard")

    def get_success_url(self):
        """Return success URL."""
        return reverse_lazy("accounts:dashboard")


class LogoutView(BaseLogoutView):
    """Logout view with success message."""

    next_page = "login"

    def dispatch(self, request, *args, **kwargs):
        """Handle logout with success message and redirect."""
        logout(request)
        messages.success(request, "Sesión cerrada correctamente.")
        return redirect("accounts:login")


class RegisterView(View):
    """Registration view for aspirants."""

    form_class = FodejasRegistrationForm
    template_name = "accounts/register.html"

    def get(self, request):
        """Show registration form."""
        if request.user.is_authenticated:
            return redirect("accounts:dashboard")
        form = self.form_class()
        return render(request, self.template_name, {"form": form})

    def post(self, request):
        """Process registration."""
        form = self.form_class(request.POST)

        if form.is_valid():
            # Create user but don't save to DB yet
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.username = form.cleaned_data["email"]  # Use email as username
            user.is_active = True  # Activate immediately (no email verification for now)
            user.save()

            # Assign R-ASPIRANTE role by default
            try:
                role_aspirante = Role.objects.get(code="R-ASPIRANTE")
                UserRole.objects.create(
                    user=user,
                    role=role_aspirante,
                    convocation_scope_id=None,
                )
            except Role.DoesNotExist:
                messages.warning(request, "Rol de aspirante no encontrado.")

            messages.success(
                request, "Registro exitoso. Ya puede iniciar sesión con sus credenciales."
            )
            return redirect("accounts:login")

        return render(request, self.template_name, {"form": form})


class PasswordResetRequestView(PasswordResetView):
    """Password reset request view."""

    form_class = FodejasPasswordResetForm
    template_name = "accounts/password_reset.html"
    email_template_name = "accounts/password_reset_email.html"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


class PasswordResetDoneView(PasswordResetDoneView):
    """Password reset done view."""

    template_name = "accounts/password_reset_done.html"


class PasswordResetConfirmView(PasswordResetConfirmView):
    """Password reset confirmation view."""

    form_class = FodejasSetPasswordForm
    template_name = "accounts/password_reset_confirm.html"
    success_url = reverse_lazy("password_reset_complete")


class PasswordResetCompleteView(PasswordResetCompleteView):
    """Password reset complete view."""

    template_name = "accounts/password_reset_complete.html"


class DashboardView(LoginRequiredMixin, PermissionMixin, TemplateView):
    """Role-based dashboard view."""

    template_name = "accounts/dashboard.html"
    login_url = "accounts:login"

    def get_context_data(self, **kwargs):
        """Add role-specific context."""
        context = super().get_context_data(**kwargs)

        user = self.request.user

        # Get user roles
        user_roles = UserRole.objects.filter(user=user).select_related("role")

        roles_data = []
        for ur in user_roles:
            roles_data.append(
                {
                    "code": ur.role.code,
                    "name": ur.role.name,
                    "type": ur.role.type,
                    "convocation": ur.convocation_scope_id,
                }
            )

        context["user"] = user
        context["roles"] = roles_data

        # Get role-specific navigation items
        context["nav_items"] = self._get_navigation_items(roles_data)

        return context

    def _get_navigation_items(self, roles):
        """Generate navigation items based on user roles."""
        nav_items = []

        for role in roles:
            if role["code"] == "R-ASPIRANTE":
                nav_items.extend(
                    [
                        {
                            "label": "Mis Postulaciones",
                            "icon": "bi-file-earmark-text",
                            "url": "/applications/",
                        },
                        {
                            "label": "Estado de Selección",
                            "icon": "bi-graph-up",
                            "url": "/applications/",
                        },
                        {
                            "label": "Convocatorias Abiertas",
                            "icon": "bi-megaphone",
                            "url": "/convocatorias/",
                        },
                    ]
                )
            elif role["code"] == "R-REVISOR":
                nav_items.extend(
                    [
                        {
                            "label": "Revisar Requisitos",
                            "icon": "bi-clipboard-check",
                            "url": "/applications/",
                        },
                        {
                            "label": "Convocatorias",
                            "icon": "bi-megaphone",
                            "url": "/convocatorias/",
                        },
                    ]
                )
            elif role["code"] == "R-COMITE":
                nav_items.extend(
                    [
                        {
                            "label": "Evaluaciones",
                            "icon": "bi-clipboard-data",
                            "url": "/applications/",
                        },
                        {"label": "Resultados", "icon": "bi-trophy", "url": "/convocatorias/"},
                    ]
                )
            elif role["code"] == "R-TESORERO":
                nav_items.extend(
                    [
                        {
                            "label": "Gestión de Pagos",
                            "icon": "bi-currency-dollar",
                            "url": "/convocatorias/",
                        },
                        {
                            "label": "Convocatorias",
                            "icon": "bi-megaphone",
                            "url": "/convocatorias/",
                        },
                    ]
                )
            elif role["code"] == "R-COORDINADOR":
                nav_items.extend(
                    [
                        {
                            "label": "Mis Convocatorias",
                            "icon": "bi-megaphone",
                            "url": "/convocatorias/",
                        },
                        {
                            "label": "Postulaciones",
                            "icon": "bi-file-earmark-text",
                            "url": "/applications/",
                        },
                        {"label": "Resultados", "icon": "bi-trophy", "url": "/convocatorias/"},
                    ]
                )
            elif role["code"] == "R-ADMIN":
                nav_items.extend(
                    [
                        {
                            "label": "Gestión de Usuarios",
                            "icon": "bi-people",
                            "url": "/accounts/admin/users/",
                        },
                        {
                            "label": "Roles y Permisos",
                            "icon": "bi-shield-check",
                            "url": "/accounts/admin/roles/",
                        },
                        {
                            "label": "Convocatorias",
                            "icon": "bi-megaphone",
                            "url": "/convocatorias/",
                        },
                        {
                            "label": "Postulaciones",
                            "icon": "bi-file-earmark-text",
                            "url": "/applications/",
                        },
                        {
                            "label": "Auditoría",
                            "icon": "bi-journal-text",
                            "url": "/accounts/audit/",
                        },
                    ]
                )

        # Add common items for all users
        nav_items.append({"label": "Mi Perfil", "icon": "bi-person", "url": "/accounts/profile/"})
        nav_items.append(
            {"label": "Mis Notificaciones", "icon": "bi-bell", "url": "/accounts/notifications/"}
        )
        nav_items.append(
            {"label": "Cerrar Sesión", "icon": "bi-box-arrow-right", "url": "/accounts/logout/"}
        )

        return nav_items


class ProfileView(LoginRequiredMixin, PermissionMixin, TemplateView):
    """User profile view."""

    template_name = "accounts/profile.html"
    login_url = "accounts:login"

    def get_context_data(self, **kwargs):
        """Add user profile data."""
        context = super().get_context_data(**kwargs)

        user = self.request.user
        user_roles = UserRole.objects.filter(user=user).select_related("role")

        roles = [ur.role.name for ur in user_roles]

        context["user"] = user
        context["roles"] = roles

        return context


class CurrentUserAPIView(APIView):
    """API view to get current user info."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Return current user info as JSON."""
        user = request.user
        user_roles = UserRole.objects.filter(user=user).select_related("role")

        roles_data = []
        for ur in user_roles:
            roles_data.append(
                {
                    "code": ur.role.code,
                    "name": ur.role.name,
                    "type": ur.role.type,
                }
            )

        return JsonResponse(
            {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "documento": user.documento,
                "roles": roles_data,
            }
        )


def root_view(request):
    """Redirect root URL to login page."""
    return redirect("accounts:login")
