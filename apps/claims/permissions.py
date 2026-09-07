"""Custom permissions for claims and appeals."""
from rest_framework.permissions import BasePermission
from django.core.exceptions import PermissionDenied


class IsTitularOrReadOnly(BasePermission):
    """Allow write only if user is the titular of the solicitud."""
    
    def has_object_permission(self, request, view, obj):
        # Read permissions are allowed for titular, OFIJUR, and admin
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        
        # Write permissions only for titular
        return obj.solicitud.aspirante == request.user


class IsTitular(BasePermission):
    """Allow only if user is the titular of the solicitud."""
    
    def has_object_permission(self, request, view, obj):
        return obj.solicitud.aspirante == request.user


class HasOFIJURRole(BasePermission):
    """Allow only if user has R-OFIJUR role."""
    
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        
        from apps.accounts.models import UserRole, Role
        ofijur_role = Role.objects.filter(code="R-OFIJUR").first()
        if not ofijur_role:
            return False
        
        return UserRole.objects.filter(user=request.user, role=ofijur_role).exists()
    
    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class HasASPIRANTERole(BasePermission):
    """Allow only if user has R-ASPIRANTE role."""
    
    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True
        
        from apps.accounts.models import UserRole, Role
        aspirante_role = Role.objects.filter(code="R-ASPIRANTE").first()
        if not aspirante_role:
            return False
        
        return UserRole.objects.filter(user=request.user, role=aspirante_role).exists()


class IsApelacionTitular(BasePermission):
    """Allow only if user is the titular of the appealed claim."""
    
    def has_object_permission(self, request, view, obj):
        return obj.reclamacion.solicitud.aspirante == request.user


class CanCreateApelacion(BasePermission):
    """Check if user can create an appeal for a specific claim."""

    def has_object_permission(self, request, view, obj):
        # CHG-805 AUD-009: ``apps.claims.services.apelaciones`` exposes
        # ``validar_apelacion`` (returns ``(is_valid, error_message)``),
        # NOT ``can_apelar``. The import name is fixed here so any DRF
        # view wired with ``permission_classes = [CanCreateApelacion]``
        # resolves at runtime.
        from apps.claims.services.apelaciones import validar_apelacion

        can_create, _ = validar_apelacion(obj, request.user)
        return can_create