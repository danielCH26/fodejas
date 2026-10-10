"""Models for accounts app."""
import uuid
from datetime import timedelta

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


def _add_working_days(start, days: int):
    """Advance ``start`` by ``days`` Mon-Fri steps.

    Returned as a ``datetime`` if ``start`` is a ``datetime``,
    else a ``date``. Negative ``days`` walks backwards.
    """
    if days == 0:
        return start
    step = timedelta(days=1 if days > 0 else -1)
    remaining = abs(days)
    cursor = start
    while remaining > 0:
        cursor = cursor + step
        if cursor.weekday() < 5:
            remaining -= 1
    return cursor


class CustomUserManager(BaseUserManager):
    """Custom manager for CustomUser using email as username."""

    def create_user(self, email, documento, password=None, **extra_fields):
        """Create and save a user with the given email and documento."""
        if not email:
            raise ValueError("El correo electrónico es requerido")
        if not documento:
            raise ValueError("El documento es requerido")

        email = self.normalize_email(email)
        user = self.model(email=email, documento=documento, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, documento, password=None, **extra_fields):
        """Create and save a superuser with the given email and documento."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, documento, password, **extra_fields)


class CustomUser(AbstractUser):
    """Custom user model for FODEJAS platform."""

    # Use custom manager
    objects = CustomUserManager()

    # UUID as primary key instead of auto-incrementing ID
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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

    # Habeas data consent tracking
    habeas_data_consent = models.DateTimeField(
        _("fecha de consentimiento de habeas data"),
        null=True,
        blank=True,
        help_text=_("Última fecha en que el usuario aceptó la política de protección de datos"),
    )

    class Meta:
        verbose_name = _("usuario")
        verbose_name_plural = _("usuarios")
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.email} ({self.get_full_name()})"


class Role(models.Model):
    """Role model for RBAC system."""

    # UUID as primary key
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

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
    group = models.OneToOneField(
        "auth.Group",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="role",
        verbose_name=_("grupo de Django"),
        help_text=_("Grupo de Django asociado para integración con sistema de permisos nativo"),
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
    # Using string reference to avoid migration order issues
    # Will be converted to ForeignKey after CAP-024
    convocation_scope_id = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_("ID de convocatoria"),
        help_text=_("ID de convocatoria específica (null para alcance global)"),
    )
    stage = models.CharField(
        _("etapa"),
        max_length=30,
        null=True,
        blank=True,
        help_text=_("Etapa específica dentro de la convocatoria (opcional)"),
    )
    auth_permission = models.OneToOneField(
        "auth.Permission",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="custom_permission",
        verbose_name=_("permiso de Django"),
        help_text=_("Permiso nativo de Django asociado a este permiso personalizado"),
    )

    class Meta:
        verbose_name = _("permiso")
        verbose_name_plural = _("permisos")
        ordering = ["app_label", "action"]
        constraints = [
            models.UniqueConstraint(
                fields=["app_label", "action", "convocation_scope_id", "stage"],
                name="unique_permission_scope",
            ),
        ]

    def __str__(self):
        scope = f" [{self.convocation_scope_id}]" if self.convocation_scope_id else ""
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
    # Note: Using convocation_scope_id CharField for migration compatibility
    # Will be converted to ForeignKey after CAP-024
    convocation_scope_id = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name=_("ID de convocatoria"),
        help_text=_("ID de convocatoria específica (null para alcance global)"),
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
                fields=["user", "role", "convocation_scope_id"],
                name="unique_user_role_scope",
            ),
        ]

    def __str__(self):
        scope = f" en {self.convocation_scope_id}" if self.convocation_scope_id else ""
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


class Consentimiento(models.Model):
    """Consentimiento para tratamiento de datos personales (Ley 1581/2012)."""

    TIPO_CHOICES = [
        ("tratamiento_datos", _("Tratamiento de Datos")),
        ("transferencia", _("Transferencia Internacional")),
    ]

    titular = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="consentimientos",
        verbose_name=_("titular"),
    )
    tipo = models.CharField(
        _("tipo de consentimiento"),
        max_length=20,
        choices=TIPO_CHOICES,
        help_text=_("Tipo de consentimiento otorgado"),
    )
    version_texto = models.TextField(
        _("texto de la versión"),
        help_text=_("Texto íntegro de la política aceptada"),
    )
    version_etiqueta = models.CharField(
        _("etiqueta de versión"),
        max_length=10,
        help_text=_("Etiqueta de versión (ej: 'v3', '2025-01')"),
    )
    hash_texto = models.CharField(
        _("hash del texto"),
        max_length=64,
        help_text=_("SHA-256 del texto de la versión (64 caracteres hex)"),
        db_index=True,
    )
    pdf_url = models.FileField(
        _("PDF firmado"),
        upload_to="consentimientos/%Y/%m/",
        help_text=_("PDF con consentimiento firmado digitalmente"),
        blank=True,
        null=True,
    )
    ip = models.GenericIPAddressField(
        _("dirección IP"),
        blank=True,
        null=True,
        help_text=_("Dirección IP desde la que se otorgó el consentimiento"),
    )
    user_agent = models.TextField(
        _("user agent"),
        blank=True,
        help_text=_("User agent del navegador al otorgar consentimiento"),
    )
    otorgado_en = models.DateTimeField(
        _("fecha de otorgamiento"),
        auto_now_add=True,
        help_text=_("Fecha y hora en que se otorgó el consentimiento"),
    )
    revocado_en = models.DateTimeField(
        _("fecha de revocación"),
        blank=True,
        null=True,
        help_text=_("Fecha y hora en que se revocó este consentimiento"),
    )

    class Meta:
        verbose_name = _("consentimiento")
        verbose_name_plural = _("consentimientos")
        ordering = ["-otorgado_en"]
        indexes = [
            models.Index(fields=["titular", "tipo"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(tipo__in=["tratamiento_datos", "transferencia"]),
                name="consentimiento_tipo_valid",
            ),
        ]

    def __str__(self):
        return f"{self.titular.email} - {self.get_tipo_display()} ({self.version_etiqueta})"


class SolicitudHabeasData(models.Model):
    """Solicitud ARCO (Acceso, Rectificación, Cancelación, Oposición) según Ley 1581/2012."""

    TIPO_CHOICES = [
        ("consulta", _("Consulta")),
        ("rectificacion", _("Rectificación")),
        ("actualizacion", _("Actualización")),
        ("supresion", _("Supresión")),
    ]

    ESTADO_CHOICES = [
        ("radicada", _("Radicada")),
        ("en_tramite", _("En Trámite")),
        ("resuelta", _("Resuelta")),
        ("rechazada", _("Rechazada")),
        ("vencida", _("Vencida")),
    ]

    titular = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="solicitudes_habeas",
        verbose_name=_("titular"),
    )
    tipo = models.CharField(
        _("tipo de solicitud"),
        max_length=15,
        choices=TIPO_CHOICES,
        help_text=_("Tipo de derecho ARCO ejercido"),
    )
    estado = models.CharField(
        _("estado de la solicitud"),
        max_length=12,
        choices=ESTADO_CHOICES,
        default="radicada",
        help_text=_("Estado actual de la solicitud"),
    )
    descripcion = models.TextField(
        _("descripción"),
        help_text=_("Descripción detallada de la solicitud"),
    )
    fecha_radicacion = models.DateTimeField(
        _("fecha de radicación"),
        auto_now_add=True,
        help_text=_("Fecha y hora en que se radicó la solicitud"),
    )
    fecha_limite = models.DateTimeField(
        _("fecha límite"),
        help_text=_("Fecha límite para resolver la solicitud (30 días hábiles)"),
    )
    respuesta = models.TextField(
        _("respuesta"),
        blank=True,
        help_text=_("Respuesta a la solicitud"),
    )
    motivo_rechazo = models.TextField(
        _("motivo de rechazo"),
        blank=True,
        help_text=_("Motivo por el cual se rechazó la solicitud"),
    )
    evidencia_url = models.FileField(
        _("evidencia"),
        upload_to="habeas-data/evidencias/%Y/%m/",
        blank=True,
        null=True,
        help_text=_("Evidencia adjunta a la respuesta"),
    )
    resuelto_por = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        related_name="solicitudes_resueltas",
        verbose_name=_("resuelto por"),
        blank=True,
        null=True,
        help_text=_("Usuario que resolvió la solicitud"),
    )
    resuelto_en = models.DateTimeField(
        _("fecha de resolución"),
        blank=True,
        null=True,
        help_text=_("Fecha y hora en que se resolvió la solicitud"),
    )
    suprimido_en = models.DateTimeField(
        _("fecha de supresión"),
        blank=True,
        null=True,
        help_text=_("Fecha y hora en que se suprimieron los datos del titular"),
    )

    class Meta:
        verbose_name = _("solicitud de habeas data")
        verbose_name_plural = _("solicitudes de habeas data")
        ordering = ["-fecha_radicacion"]
        indexes = [
            models.Index(fields=["estado"]),
            models.Index(fields=["fecha_limite"]),
            models.Index(fields=["titular", "tipo"]),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(tipo__in=["consulta", "rectificacion", "actualizacion", "supresion"]),
                name="solicitud_tipo_valid",
            ),
            models.CheckConstraint(
                check=models.Q(estado__in=["radicada", "en_tramite", "resuelta", "rechazada", "vencida"]),
                name="solicitud_estado_valid",
            ),
        ]

    def __str__(self):
        return f"{self.titular.email} - {self.get_tipo_display()} ({self.get_estado_display()})"

    def save(self, *args, **kwargs):
        """Autocompute ``fecha_limite`` for the 30-working-day window (CAP-025).

        Ley 1581/2012 and Decreto 1377/2013 establish that ARCO
        requests must be resolved within 30 *working* days
        (lunes a viernes) from the moment they are received.

        Implementation note: ``fecha_radicacion`` uses
        ``auto_now_add=True`` which Django applies in
        ``Model.save_base()`` AFTER our ``save()`` override runs.
        Therefore on a fresh insert we must set
        ``fecha_radicacion`` ourselves before computing
        ``fecha_limite``. The override is a no-op when:
          - ``fecha_limite`` is already set (caller supplied an
            explicit value), or
          - this is an update of an existing row whose
            ``fecha_radicacion`` is already populated.
        """
        if self.pk is None and getattr(self, "fecha_radicacion", None) is None:
            self.fecha_radicacion = timezone.now()
        if (
            self.fecha_limite is None
            and getattr(self, "fecha_radicacion", None) is not None
        ):
            # 30 working days = up to 42 calendar days. Walk forward
            # one calendar day at a time, counting only Mon-Fri.
            self.fecha_limite = _add_working_days(
                self.fecha_radicacion, 30
            )
        super().save(*args, **kwargs)


class Notification(models.Model):
    """In-app notification for users."""

    TIPO_CHOICES = [
        ("info", _("Info")),
        ("warning", _("Advertencia")),
        ("success", _("Éxito")),
        ("error", _("Error")),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="notifications",
        verbose_name=_("destinatario"),
    )
    event = models.CharField(
        _("evento"),
        max_length=64,
        help_text=_("Código estable del evento (ej: 'habeas.created', 'application.submitted')"),
    )
    tipo = models.CharField(
        _("tipo"),
        max_length=16,
        choices=TIPO_CHOICES,
        default="info",
        help_text=_("Tipo de notificación"),
    )
    titulo = models.CharField(
        _("título"),
        max_length=140,
        help_text=_("Título breve de la notificación"),
    )
    mensaje = models.TextField(
        _("mensaje"),
        help_text=_("Mensaje detallado (PII debe estar enmascarado)"),
    )
    payload = models.JSONField(
        _("payload"),
        default=dict,
        help_text=_("Datos adicionales saneados (sin PII)"),
    )
    read_at = models.DateTimeField(
        _("fecha de lectura"),
        null=True,
        blank=True,
        help_text=_("Fecha y hora en que el usuario marcó la notificación como leída"),
    )
    created_at = models.DateTimeField(
        _("fecha de creación"),
        auto_now_add=True,
    )
    created_date = models.DateField(
        _("fecha (día)"),
        auto_now_add=True,
        help_text=_("Fecha del día para idempotencia diaria"),
    )
    dispatched_at = models.DateTimeField(
        _("fecha de despacho"),
        null=True,
        blank=True,
        help_text=_("Fecha y hora en que se despachó a auditoría"),
    )
    repeat_count = models.PositiveIntegerField(
        _("contador de repeticiones"),
        default=1,
        help_text=_("Número de veces que se repitió el mismo evento en el mismo día"),
    )

    class Meta:
        verbose_name = _("notificación")
        verbose_name_plural = _("notificaciones")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "read_at", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["recipient", "event", "created_date"],
                name="unique_notification_per_day",
            ),
        ]

    def __str__(self):
        return f"{self.event} → {self.recipient.email}"

    @property
    def leido(self):
        """Derived property indicating if notification has been read."""
        return self.read_at is not None
