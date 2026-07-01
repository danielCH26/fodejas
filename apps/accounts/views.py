"""Views for accounts app."""
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView as BaseLoginView,
    LogoutView as BaseLogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from rest_framework import permissions, status
from rest_framework.views import APIView
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from .forms import (
    FodejasLoginForm,
    FodejasPasswordResetForm,
    FodejasRegistrationForm,
    FodejasSetPasswordForm,
)
from .models import Role, UserRole

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
        user_roles = UserRole.objects.filter(user=user).select_related("role", "convocation_scope")

        roles_data = []
        for ur in user_roles:
            roles_data.append({
                "code": ur.role.code,
                "name": ur.role.name,
                "type": ur.role.type,
                "convocation": ur.convocation_scope_id,
            })

        # If AJAX request, return JSON with tokens
        if self.request.headers.get("HX-Request"):
            # For HTMX requests, just return success
            return render(self.request, "accounts/partials/login_success.html", {
                "user": user,
                "roles": roles_data,
            })

        # For regular form submission, redirect to dashboard
        login(self.request, user)
        return redirect("dashboard")

    def get_success_url(self):
        """Return success URL."""
        return reverse_lazy("dashboard")


class LogoutView(BaseLogoutView):
    """Logout view with token blacklist."""

    next_page = "login"

    def dispatch(self, request, *args, **kwargs):
        """Handle logout."""
        logout(request)
        messages.success(request, "Sesión cerrada correctamente.")
        return super().dispatch(request, *args, **kwargs)


class RegisterView(View):
    """Registration view for aspirants."""

    form_class = FodejasRegistrationForm
    template_name = "accounts/register.html"

    def get(self, request):
        """Show registration form."""
        if request.user.is_authenticated:
            return redirect("dashboard")
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
                    convocation_scope=None,
                )
            except Role.DoesNotExist:
                messages.warning(request, "Rol de aspirante no encontrado.")

            messages.success(
                request,
                "Registro exitoso. Ya puede iniciar sesión con sus credenciales."
            )
            return redirect("login")

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


class DashboardView(LoginRequiredMixin, TemplateView):
    """Role-based dashboard view."""

    template_name = "accounts/dashboard.html"
    login_url = "login"

    def get_context_data(self, **kwargs):
        """Add role-specific context."""
        context = super().get_context_data(**kwargs)

        user = self.request.user

        # Get user roles
        user_roles = UserRole.objects.filter(user=user).select_related(
            "role", "convocation_scope"
        )

        roles_data = []
        for ur in user_roles:
            roles_data.append({
                "code": ur.role.code,
                "name": ur.role.name,
                "type": ur.role.type,
                "convocation": ur.convocation_scope.titulo if ur.convocation_scope else None,
            })

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
                nav_items.extend([
                    {"label": "Mis Postulaciones", "icon": "bi-file-earmark-text", "url": "#"},
                    {"label": "Estado de Selección", "icon": "bi-graph-up", "url": "#"},
                ])
            elif role["code"] == "R-BENEF":
                nav_items.extend([
                    {"label": "Mi Crédito", "icon": "bi-currency-dollar", "url": "#"},
                    {"label": "Seguimiento Académico", "icon": "bi-book", "url": "#"},
                ])
            elif role["code"] in ["R-COORD", "R-CT"]:
                nav_items.extend([
                    {"label": "Convocatorias", "icon": "bi-megaphone", "url": "#"},
                    {"label": "Evaluación", "icon": "bi-clipboard-check", "url": "#"},
                    {"label": "Resultados", "icon": "bi-trophy", "url": "#"},
                ])
            elif role["code"] == "R-ADMIN":
                nav_items.extend([
                    {"label": "Usuarios", "icon": "bi-people", "url": "#"},
                    {"label": "Roles", "icon": "bi-shield-check", "url": "#"},
                    {"label": "Configuración", "icon": "bi-gear", "url": "#"},
                ])

        # Add common items
        nav_items.append({"label": "Mis Notificaciones", "icon": "bi-bell", "url": "#"})

        return nav_items


class ProfileView(LoginRequiredMixin, TemplateView):
    """User profile view."""

    template_name = "accounts/profile.html"
    login_url = "login"

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
            roles_data.append({
                "code": ur.role.code,
                "name": ur.role.name,
                "type": ur.role.type,
            })

        return JsonResponse({
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "documento": user.documento,
            "roles": roles_data,
        })
