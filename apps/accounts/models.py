"""Models for accounts app."""
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class CustomUser(AbstractUser):
    """Custom user model for FODEJAS platform."""

    # Remove username field since we're using email as username
    username = None

    # Documento de identidad (unique, at least 6 characters)
    documento = models.CharField(
        _("documento de identidad"),
        max_length=20,
        unique=True,
        validators=[MinLengthValidator(6)],
        help_text=_("Documento de identidad único (mínimo 6 caracteres)"),
    )

    # Email is already inherited from AbstractUser but we need to make it unique
    email = models.EmailField(
        _("correo electrónico"),
        unique=True,
        help_text=_("Correo electrónico único para inicio de sesión"),
    )

    # Phone number in E.164 format
    telefono = models.CharField(
        _("teléfono"),
        max_length=20,
        blank=True,
        help_text=_("Número de teléfono en formato E.164"),
    )

    # Date of birth (must be at least 14 years old)
    fecha_nacimiento = models.DateField(
        _("fecha de nacimiento"),
        null=True,
        blank=True,
        help_text=_("Fecha de nacimiento (mínimo 14 años)"),
    )

    # Track last activity for JWT session timeout
    last_activity = models.DateTimeField(
        _("última actividad"),
        auto_now=True,
        help_text=_("Última vez que el usuario interactuó con el sistema"),
    )

    # Set email as the USERNAME_FIELD
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["documento", "first_name", "last_name"]

    class Meta:
        verbose_name = _("usuario")
        verbose_name_plural = _("usuarios")
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"


class Role(models.Model):
    """Role model for RBAC system."""

    ROLE_TYPE_CHOICES = [
        ("interno", _("Interno")),
        ("externo", _("Externo")),
    ]

    code = models.CharField(
        _("código de rol"),
        max_length=16,
        unique=True,
        help_text=_("Código único del rol (ej: R-ASPIRANTE)"),
    )
    name = models.CharField(
        _("nombre del rol"),
        max_length=80,
        help_text=_("Nombre descriptivo del rol"),
    )
    type = models.CharField(
        _("tipo de rol"),
        max_length=8,
        choices=ROLE_TYPE_CHOICES,
        help_text=_("Tipo de rol (interno para personal, externo para beneficiarios/ciudadanos)"),
    )
    description = models.TextField(
        _("descripción"),
        blank=True,
        help_text=_("Descripción detallada del rol y sus responsabilidades"),
    )

    class Meta:
        verbose_name = _("rol")
        verbose_name_plural = _("roles")
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(type__in=["interno", "externo"]),
                name="role_type_valid",
            ),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"


class Permission(models.Model):
    """Permission model for granular access control."""

    app_label = models.CharField(
        _("etiqueta de aplicación"),
        max_length=100,
        help_text=_("Etiqueta de la aplicación Django (ej: 'applications')"),
    )
    action = models.CharField(
        _("acción"),
        max_length=50,
        help_text=_("Acción permitida (ej: 'add_application', 'view_convocatory')"),
    )
    # Note: convocatoria.Convocatory doesn't exist yet (CAP-002)
    # Using string reference for now
    convocation_scope = models.ForeignKey(
        "convocatories.Convocatory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("alcance por convocatoria"),
        help_text=_("Convocatoria específica (null para alcance global)"),
    )
    stage = models.CharField(
        _("etapa"),
        max_length=30,
        null=True,
        blank=True,
        help_text=_("Etapa específica dentro de la convocatoria (opcional)"),
    )

    class Meta:
        verbose_name = _("permiso")
        verbose_name_plural = _("permisos")
        ordering = ["app_label", "action"]
        constraints = [
            models.UniqueConstraint(
                fields=["app_label", "action", "convocation_scope", "stage"],
                name="unique_permission_scope",
            ),
        ]

    def __str__(self):
        scope = f" [{self.convocation_scope}]" if self.convocation_scope else ""
        stage = f" ({self.stage})" if self.stage else ""
        return f"{self.app_label}.{self.action}{scope}{stage}"


class UserRole(models.Model):
    """Association between users and roles with optional convocation scope."""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="user_roles",
        verbose_name=_("usuario"),
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="user_roles",
        verbose_name=_("rol"),
    )
    # Note: convocatoria.Convocatory doesn't exist yet (CAP-002)
    # Using string reference for now
    convocation_scope = models.ForeignKey(
        "convocatories.Convocatory",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_("alcance por convocatoria"),
        help_text=_("Convocatoria específica (null para alcance global del rol)"),
    )
    created_at = models.DateTimeField(
        _("fecha de asignación"),
        auto_now_add=True,
    )

    class Meta:
        verbose_name = _("asignación de rol")
        verbose_name_plural = _("asignaciones de roles")
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "role", "convocation_scope"],
                name="unique_user_role_scope",
            ),
        ]

    def __str__(self):
        scope = f" en {self.convocation_scope}" if self.convocation_scope else ""
        return f"{self.user.email} → {self.role.code}{scope}"


class RolePermission(models.Model):
    """Association between roles and permissions."""

    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_permissions",
        verbose_name=_("rol"),
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE,
        related_name="role_permissions",
        verbose_name=_("permiso"),
    )

    class Meta:
        verbose_name = _("permiso de rol")
        verbose_name_plural = _("permisos de roles")
        ordering = ["role", "permission"]
        constraints = [
            models.UniqueConstraint(
                fields=["role", "permission"],
                name="unique_role_permission",
            ),
        ]

    def __str__(self):
        return f"{self.role.code} → {self.permission}"