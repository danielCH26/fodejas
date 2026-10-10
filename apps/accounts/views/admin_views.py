"""Admin views for user and role management."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    TemplateView,
)

from apps.accounts.models import Role, UserRole
from apps.accounts.permissions import IsAdminRole
from apps.accounts.services.assignment import assign_role_to_user, revoke_role_from_user
from apps.audit.models import AuditEvent
from apps.audit.services import log_audit_event

User = get_user_model()


class BaseAdminView(LoginRequiredMixin, TemplateView):
    """Base view for admin pages with R-ADMIN role check."""

    permission_class = IsAdminRole
    login_url = reverse_lazy("accounts:login")

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(self.login_url)

        # Check for R-ADMIN role
        has_admin_role = request.user.user_roles.filter(role__code='R-ADMIN').exists()
        is_superuser = request.user.is_superuser or request.user.is_staff

        if not (has_admin_role or is_superuser):
            messages.error(request, "No tienes permisos de administrador.")
            return redirect("dashboard")

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["admin_section"] = getattr(self, "admin_section", "admin")
        return context


class UserListView(BaseAdminView):
    """List all users with filters and search."""

    admin_section = "users"
    template_name = "accounts/admin/users/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get query params
        search = self.request.GET.get("search", "")
        role_filter = self.request.GET.get("role", "")
        status_filter = self.request.GET.get("status", "active")

        # Base queryset
        users = User.objects.select_related().order_by("-date_joined")

        # Apply filters
        if search:
            users = users.filter(
                Q(email__icontains=search) |
                Q(documento__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )

        if role_filter:
            users = users.filter(user_roles__role__code=role_filter).distinct()

        if status_filter == "active":
            users = users.filter(is_active=True)
        elif status_filter == "inactive":
            users = users.filter(is_active=False)

        context["users"] = users
        context["roles"] = Role.objects.all()
        context["search"] = search
        context["role_filter"] = role_filter
        context["status_filter"] = status_filter

        return context


class UserCreateView(BaseAdminView):
    """Create a new user."""

    admin_section = "users"
    template_name = "accounts/admin/users/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = "crear"
        return context

    def post(self, request, *args, **kwargs):
        email = request.POST.get("email", "").strip().lower()
        documento = request.POST.get("documento", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        telefono = request.POST.get("telefono", "").strip()

        # Validation
        errors = []

        if not email:
            errors.append("El email es requerido.")
        elif User.objects.filter(email__iexact=email).exists():
            errors.append("Ya existe un usuario con este email.")

        if not documento:
            errors.append("El documento es requerido.")
        elif User.objects.filter(documento=documento).exists():
            errors.append("Ya existe un usuario con este documento.")

        if not first_name:
            errors.append("El nombre es requerido.")

        if not last_name:
            errors.append("El apellido es requerido.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return self.get(request, *args, **kwargs)

        # Generate temporary password
        import secrets
        temp_password = secrets.token_urlsafe(8)

        # Create user
        user = User.objects.create_user(
            email=email,
            documento=documento,
            password=temp_password,
            first_name=first_name,
            last_name=last_name,
            telefono=telefono if telefono else "",
        )

        # Log audit
        log_audit_event(
            user=request.user,
            action="user_created",
            details={
                "email": email,
                "documento": documento,
                "user_id": user.id,
            },
        )

        messages.success(request, f"Usuario {email} creado exitosamente.")
        return redirect("accounts_admin:user_detail", pk=user.id)


class UserDetailView(BaseAdminView):
    """View user details."""

    admin_section = "users"
    template_name = "accounts/admin/users/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(User, pk=self.kwargs["pk"])

        # Get user roles
        user_roles = UserRole.objects.filter(user=user).select_related("role")

        # Get recent audit events for this user
        recent_logs = AuditEvent.objects.filter(
            actor=user
        ).order_by("-timestamp")[:10]

        context["view_user"] = user
        context["user_roles"] = user_roles
        context["recent_logs"] = recent_logs

        return context


class UserUpdateView(BaseAdminView):
    """Update user details."""

    admin_section = "users"
    template_name = "accounts/admin/users/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(User, pk=self.kwargs["pk"])
        context["view_user"] = user
        context["action"] = "editar"
        return context

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=self.kwargs["pk"])

        email = request.POST.get("email", "").strip().lower()
        documento = request.POST.get("documento", "").strip()
        first_name = request.POST.get("first_name", "").strip()
        last_name = request.POST.get("last_name", "").strip()
        telefono = request.POST.get("telefono", "").strip()

        # Validation
        errors = []

        if not email:
            errors.append("El email es requerido.")
        elif User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
            errors.append("Ya existe otro usuario con este email.")

        if not documento:
            errors.append("El documento es requerido.")
        elif User.objects.filter(documento=documento).exclude(pk=user.pk).exists():
            errors.append("Ya existe otro usuario con este documento.")

        if not first_name:
            errors.append("El nombre es requerido.")

        if not last_name:
            errors.append("El apellido es requerido.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return self.get(request, *args, **kwargs)

        # Track changes
        changes = []
        if user.email != email:
            changes.append(f"email: {user.email} -> {email}")
        if user.documento != documento:
            changes.append(f"documento: {user.documento} -> {documento}")

        # Update user
        user.email = email
        user.documento = documento
        user.first_name = first_name
        user.last_name = last_name
        user.telefono = telefono if telefono else ""
        user.save()

        # Log audit
        log_audit_event(
            user=request.user,
            action="user_updated",
            details={
                "user_id": user.id,
                "email": email,
                "changes": changes,
            },
        )

        messages.success(request, f"Usuario {email} actualizado exitosamente.")
        return redirect("accounts_admin:user_detail", pk=user.pk)


class UserToggleActiveView(BaseAdminView):
    """Toggle user active status."""

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs["pk"])

        # Prevent deactivating yourself
        if user == request.user:
            messages.error(request, "No puedes desactivar tu propia cuenta.")
            return redirect("accounts_admin:user_detail", pk=user.pk)

        user.is_active = not user.is_active
        user.save()

        action = "activado" if user.is_active else "desactivado"

        # Log audit
        log_audit_event(
            user=request.user,
            action="user_toggled",
            details={
                "user_id": user.id,
                "email": user.email,
                "new_status": "active" if user.is_active else "inactive",
            },
        )

        messages.success(request, f"Usuario {user.email} {action} exitosamente.")
        return redirect("accounts_admin:user_detail", pk=user.pk)


class UserRoleAssignView(BaseAdminView):
    """Assign role to user."""

    admin_section = "users"
    template_name = "accounts/admin/users/roles.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(User, pk=self.kwargs["pk"])

        # Get user's current roles
        current_roles = UserRole.objects.filter(user=user).select_related("role")

        # Get all available roles
        current_role_ids = current_roles.values_list("role_id", flat=True)
        available_roles = Role.objects.exclude(id__in=current_role_ids)

        context["view_user"] = user
        context["current_roles"] = current_roles
        context["available_roles"] = available_roles

        return context

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs["pk"])
        role_id = request.POST.get("role_id")
        convocation_scope = request.POST.get("convocation_scope", "").strip() or None

        if not role_id:
            messages.error(request, "Debes seleccionar un rol.")
            return redirect("accounts_admin:user_roles", pk=user.pk)

        role = get_object_or_404(Role, pk=role_id)

        # Check if already has role
        if UserRole.objects.filter(user=user, role=role).exists():
            messages.warning(request, f"El usuario ya tiene el rol {role.name}.")
            return redirect("accounts_admin:user_roles", pk=user.pk)

        # Assign role using the service (adds to Django group too)
        assign_role_to_user(
            user=user,
            role=role,
            convocation_scope=convocation_scope,
            actor=request.user,
        )

        messages.success(request, f"Rol {role.name} asignado a {user.email}.")
        return redirect("accounts_admin:user_detail", pk=user.pk)


class UserRoleRevokeView(BaseAdminView):
    """Revoke role from user."""

    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs["pk"])
        role = get_object_or_404(Role, pk=kwargs["role_id"])

        user_role = UserRole.objects.filter(user=user, role=role).first()

        if not user_role:
            messages.error(request, "El usuario no tiene ese rol.")
            return redirect("accounts_admin:user_detail", pk=user.pk)

        # Revoke role using the service (removes from Django group too)
        revoke_role_from_user(
            user_role=user_role,
            actor=request.user,
        )

        messages.success(request, f"Rol {role.name} eliminado de {user.email}.")
        return redirect("accounts_admin:user_detail", pk=user.pk)


# Role Management Views


class RoleListView(BaseAdminView):
    """List all roles."""

    admin_section = "roles"
    template_name = "accounts/admin/roles/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["roles"] = Role.objects.all().order_by("code")
        return context


class RoleCreateView(BaseAdminView):
    """Create a new role."""

    admin_section = "roles"
    template_name = "accounts/admin/roles/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = "crear"
        return context

    def post(self, request, *args, **kwargs):
        code = request.POST.get("code", "").strip().upper()
        name = request.POST.get("name", "").strip()
        role_type = request.POST.get("type", "interno")
        description = request.POST.get("description", "").strip()

        # Validation
        errors = []

        if not code:
            errors.append("El código del rol es requerido.")
        elif Role.objects.filter(code__iexact=code).exists():
            errors.append("Ya existe un rol con este código.")

        if not name:
            errors.append("El nombre del rol es requerido.")

        if role_type not in ["interno", "externo"]:
            errors.append("Tipo de rol inválido.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return self.get(request, *args, **kwargs)

        # Create role
        role = Role.objects.create(
            code=code,
            name=name,
            type=role_type,
            description=description,
        )

        # Log audit
        log_audit_event(
            user=request.user,
            action="role_created",
            details={
                "role_id": role.id,
                "role_code": code,
                "role_name": name,
            },
        )

        messages.success(request, f"Rol {name} creado exitosamente.")
        return redirect("accounts_admin:role_detail", pk=role.pk)


class RoleDetailView(BaseAdminView):
    """View role details."""

    admin_section = "roles"
    template_name = "accounts/admin/roles/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = get_object_or_404(Role, pk=self.kwargs["pk"])

        # Get users with this role
        user_roles = UserRole.objects.filter(role=role).select_related("user")

        context["view_role"] = role
        context["user_roles"] = user_roles
        context["user_count"] = user_roles.count()

        return context


class RoleUpdateView(BaseAdminView):
    """Update role."""

    admin_section = "roles"
    template_name = "accounts/admin/roles/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = get_object_or_404(Role, pk=self.kwargs["pk"])
        context["view_role"] = role
        context["action"] = "editar"
        return context

    def post(self, request, *args, **kwargs):
        role = get_object_or_404(Role, pk=kwargs["pk"])

        name = request.POST.get("name", "").strip()
        role_type = request.POST.get("type", "interno")
        description = request.POST.get("description", "").strip()

        # Validation
        errors = []

        if not name:
            errors.append("El nombre del rol es requerido.")

        if role_type not in ["interno", "externo"]:
            errors.append("Tipo de rol inválido.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return self.get(request, *args, **kwargs)

        # Track changes
        changes = []
        if role.name != name:
            changes.append(f"name: {role.name} -> {name}")
        if role.type != role_type:
            changes.append(f"type: {role.type} -> {role_type}")

        # Update role
        role.name = name
        role.type = role_type
        role.description = description
        role.save()

        # Log audit
        log_audit_event(
            user=request.user,
            action="role_updated",
            details={
                "role_id": role.id,
                "role_code": role.code,
                "changes": changes,
            },
        )

        messages.success(request, f"Rol {name} actualizado exitosamente.")
        return redirect("accounts_admin:role_detail", pk=role.pk)


class UserRoleHistoryView(BaseAdminView):
    """Show role change history for a user."""

    admin_section = "users"
    template_name = "accounts/admin/users/role_history.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(User, pk=self.kwargs["pk"])

        # Get audit events for role assignments/revocations

        role_events = AuditEvent.objects.filter(
            entity="UserRole",
        ).filter(
            # Filter events related to this user
            details__contains=str(user.id)
        ).order_by("-timestamp")[:50]

        context["view_user"] = user
        context["role_events"] = role_events

        return context
