"""Admin views for user and role management."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView, DetailView, ListView, TemplateView, UpdateView, View
)

from apps.audit.models import AuditLog
from apps.accounts.models import Role, UserRole
from apps.accounts.forms.admin import (
    UserAdminForm, 
    RoleAdminForm, 
    UserRoleAssignForm,
    UserUpdateAdminForm
)
from apps.accounts.permissions import IsAdminRole

User = get_user_model()


class BaseAdminView(LoginRequiredMixin, TemplateView):
    """Base view for admin pages."""
    permission_required = 'R-ADMIN'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['admin_section'] = self.admin_section
        return context
    
    def dispatch(self, request, *args, **kwargs):
        # Check if user has R-ADMIN role
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        if not IsAdminRole().has_permission(request, self):
            return self.handle_no_permission()
        
        return super().dispatch(request, *args, **kwargs)


class UserListView(BaseAdminView, ListView):
    """List all users with filters and search."""
    model = User
    template_name = 'accounts/admin/users/list.html'
    context_object_name = 'users'
    admin_section = 'users'
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-date_joined')
        
        # Filter by status
        status_filter = self.request.GET.get('status', '')
        if status_filter == 'active':
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Filter by role
        role_filter = self.request.GET.get('role', '')
        if role_filter:
            queryset = queryset.filter(user_roles__role__code=role_filter).distinct()
        
        # Search by email or documento
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                email__icontains=search
            ) | queryset.filter(
                documento__icontains=search
            ) | queryset.filter(
                first_name__icontains=search
            ) | queryset.filter(
                last_name__icontains=search
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_filter'] = self.request.GET.get('status', '')
        context['role_filter'] = self.request.GET.get('role', '')
        context['search'] = self.request.GET.get('search', '')
        context['role_choices'] = Role.objects.all()
        return context


class UserCreateView(BaseAdminView, CreateView):
    """Create a new user."""
    model = User
    form_class = UserAdminForm
    template_name = 'accounts/admin/users/form.html'
    success_url = reverse_lazy('accounts_admin:user_list')
    admin_section = 'users'
    
    def form_valid(self, form):
        """Handle valid form submission."""
        # Generate a random password for the new user
        import secrets
        import string
        password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
        
        # Create the user with the temporary password
        user = form.save(commit=False)
        user.set_password(password)
        user.save()
        
        # Log the action in audit log
        AuditLog.objects.create(
            action='user_created',
            details={
                'user_id': user.id,
                'email': user.email,
                'documento': user.documento,
                'created_by': self.request.user.email,
            },
            actor=self.request.user,
        )
        
        messages.success(
            self.request,
            f"Usuario {user.email} creado exitosamente. Contraseña temporal: {password}"
        )
        
        return redirect('accounts_admin:user_detail', pk=user.pk)


class UserDetailView(BaseAdminView, DetailView):
    """View user details and activity history."""
    model = User
    template_name = 'accounts/admin/users/detail.html'
    context_object_name = 'user_obj'
    admin_section = 'users'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        
        # Get user's roles
        user_roles = UserRole.objects.filter(user=user).select_related('role')
        context['user_roles'] = user_roles
        
        # Get audit logs for this user
        audit_logs = AuditLog.objects.filter(
            details__user_id=user.id
        ).order_by('-timestamp')[:20]
        context['audit_logs'] = audit_logs
        
        return context


class UserUpdateView(BaseAdminView, UpdateView):
    """Update user information."""
    model = User
    form_class = UserUpdateAdminForm
    template_name = 'accounts/admin/users/form.html'
    admin_section = 'users'
    
    def get_success_url(self):
        return reverse_lazy('accounts_admin:user_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Handle valid form submission."""
        user = form.save()
        
        # Log the action in audit log
        AuditLog.objects.create(
            action='user_updated',
            details={
                'user_id': user.id,
                'email': user.email,
                'updated_by': self.request.user.email,
                'changes': form.changed_data,
            },
            actor=self.request.user,
        )
        
        messages.success(self.request, "Usuario actualizado exitosamente.")
        return super().form_valid(form)


class UserToggleActiveView(BaseAdminView, View):
    """Toggle user active status."""
    
    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs['pk'])
        
        # Prevent deactivating the last admin
        if not user.is_active and user.user_roles.filter(role__code='R-ADMIN').exists():
            # Check if this is the only admin
            active_admins = User.objects.filter(
                is_active=True,
                user_roles__role__code='R-ADMIN'
            ).exclude(pk=user.pk).count()
            
            if active_admins == 0:
                messages.error(
                    request,
                    "No se puede desactivar el último administrador activo del sistema."
                )
                return redirect('accounts_admin:user_detail', pk=user.pk)
        
        # Toggle active status
        user.is_active = not user.is_active
        user.save()
        
        # Log the action
        action = 'user_activated' if user.is_active else 'user_deactivated'
        AuditLog.objects.create(
            action=action,
            details={
                'user_id': user.id,
                'email': user.email,
                'action_by': request.user.email,
                'new_status': 'active' if user.is_active else 'inactive',
            },
            actor=request.user,
        )
        
        status_msg = "activado" if user.is_active else "desactivado"
        messages.success(request, f"Usuario {status_msg} exitosamente.")
        
        return redirect('accounts_admin:user_detail', pk=user.pk)


class RoleListView(BaseAdminView, ListView):
    """List all roles."""
    model = Role
    template_name = 'accounts/admin/roles/list.html'
    context_object_name = 'roles'
    admin_section = 'roles'


class RoleCreateView(BaseAdminView, CreateView):
    """Create a new role."""
    model = Role
    form_class = RoleAdminForm
    template_name = 'accounts/admin/roles/form.html'
    success_url = reverse_lazy('accounts_admin:role_list')
    admin_section = 'roles'
    
    def form_valid(self, form):
        """Handle valid form submission."""
        role = form.save()
        
        # Log the action in audit log
        AuditLog.objects.create(
            action='role_created',
            details={
                'role_id': role.id,
                'code': role.code,
                'name': role.name,
                'created_by': self.request.user.email,
            },
            actor=self.request.user,
        )
        
        messages.success(self.request, "Rol creado exitosamente.")
        return super().form_valid(form)


class RoleDetailView(BaseAdminView, DetailView):
    """View role details and users assigned."""
    model = Role
    template_name = 'accounts/admin/roles/detail.html'
    context_object_name = 'role'
    admin_section = 'roles'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        role = self.get_object()
        
        # Get users with this role
        user_roles = UserRole.objects.filter(role=role).select_related('user')
        context['user_roles'] = user_roles
        
        return context


class RoleUpdateView(BaseAdminView, UpdateView):
    """Update role information."""
    model = Role
    form_class = RoleAdminForm
    template_name = 'accounts/admin/roles/form.html'
    admin_section = 'roles'
    
    def get_success_url(self):
        return reverse_lazy('accounts_admin:role_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Handle valid form submission."""
        role = form.save()
        
        # Log the action in audit log
        AuditLog.objects.create(
            action='role_updated',
            details={
                'role_id': role.id,
                'code': role.code,
                'updated_by': self.request.user.email,
                'changes': form.changed_data,
            },
            actor=self.request.user,
        )
        
        messages.success(self.request, "Rol actualizado exitosamente.")
        return super().form_valid(form)


class UserRoleAssignView(BaseAdminView, TemplateView):
    """Assign roles to a user."""
    template_name = 'accounts/admin/users/assign_role.html'
    admin_section = 'users'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = get_object_or_404(User, pk=kwargs['pk'])
        
        context['user'] = user
        context['user_roles'] = UserRole.objects.filter(user=user).select_related('role')
        context['available_roles'] = Role.objects.exclude(
            pk__in=context['user_roles'].values_list('role_id', flat=True)
        )
        context['form'] = UserRoleAssignForm()
        
        return context
    
    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs['pk'])
        form = UserRoleAssignForm(request.POST)
        
        if form.is_valid():
            role = form.cleaned_data['role']
            convocation_scope_id = form.cleaned_data.get('convocation_scope_id')
            
            # Check if role is already assigned
            existing_role = UserRole.objects.filter(
                user=user, 
                role=role,
                convocation_scope_id=convocation_scope_id
            ).first()
            
            if existing_role:
                messages.info(request, f"El usuario ya tiene asignado el rol {role.code} con este alcance.")
            else:
                # Assign the role
                user_role = UserRole.objects.create(
                    user=user,
                    role=role,
                    convocation_scope_id=convocation_scope_id
                )
                
                # Log the action in audit log
                AuditLog.objects.create(
                    action='role_assigned',
                    details={
                        'user_id': user.id,
                        'role_id': role.id,
                        'role_code': role.code,
                        'convocation_scope': convocation_scope_id,
                        'assigned_by': request.user.email,
                    },
                    actor=request.user,
                )
                
                messages.success(request, f"Rol {role.code} asignado exitosamente.")
        
        return redirect('accounts_admin:user_role_assign', pk=user.pk)


class UserRoleRevokeView(BaseAdminView, View):
    """Revoke a role from a user."""
    
    def post(self, request, *args, **kwargs):
        user = get_object_or_404(User, pk=kwargs['user_pk'])
        role = get_object_or_404(Role, pk=kwargs['role_pk'])
        
        # Find the UserRole to revoke
        user_role = UserRole.objects.filter(user=user, role=role).first()
        
        if not user_role:
            messages.error(request, "El usuario no tiene asignado este rol.")
        else:
            # Check if this is the last role
            role_count = UserRole.objects.filter(user=user).count()
            
            if role_count == 1:
                messages.warning(
                    request,
                    "El usuario quedará sin roles. Asegúrese de asignar al menos un rol."
                )
            
            # Revoke the role
            user_role.delete()
            
            # Log the action in audit log
            AuditLog.objects.create(
                action='role_revoked',
                details={
                    'user_id': user.id,
                    'role_id': role.id,
                    'role_code': role.code,
                    'revoked_by': request.user.email,
                },
                actor=request.user,
            )
            
            messages.success(request, f"Rol {role.code} revocado exitosamente.")
        
        return redirect('accounts_admin:user_role_assign', pk=user.pk)