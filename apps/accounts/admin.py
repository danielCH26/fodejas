"""Admin configuration for accounts app."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import (
    CustomUser,
    Role,
    Permission,
    UserRole,
    RolePermission,
    Consentimiento,
    SolicitudHabeasData,
    Notification,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """Admin configuration for CustomUser."""
    list_display = (
        "email",
        "documento",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
    )
    list_filter = ("is_staff", "is_active", "date_joined")
    search_fields = ("email", "documento", "first_name", "last_name")
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            _("Información Personal"),
            {
                "fields": (
                    "documento",
                    "first_name",
                    "last_name",
                    "telefono",
                    "fecha_nacimiento",
                    "habeas_data_consent",
                )
            },
        ),
        (
            _("Permisos"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (_("Fechas importantes"), {"fields": ("last_login", "date_joined", "last_activity")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "documento",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                ),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    """Admin configuration for Role."""
    list_display = ("code", "name", "type", "description")
    list_filter = ("type",)
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    """Admin configuration for Permission."""
    list_display = ("app_label", "action", "convocation_scope_id", "stage")
    list_filter = ("app_label",)
    search_fields = ("app_label", "action")
    ordering = ("app_label", "action")


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    """Admin configuration for UserRole."""
    list_display = ("user", "role", "convocation_scope_id", "created_at")
    list_filter = ("role",)
    search_fields = ("user__email", "role__code")
    ordering = ("-created_at",)


@admin.register(RolePermission)
class RolePermissionAdmin(admin.ModelAdmin):
    """Admin configuration for RolePermission."""
    list_display = ("role", "permission")
    list_filter = ("role",)
    search_fields = ("role__code", "permission__action")
    ordering = ("role", "permission")


class ConsentimientoAdmin(admin.ModelAdmin):
    """Admin configuration for Consentimiento."""
    list_display = ("titular_email", "tipo", "version_etiqueta", "otorgado_en", "revocado_en")
    list_filter = ("tipo", "revocado_en")
    search_fields = ("titular__email", "version_etiqueta")
    readonly_fields = ("hash_texto", "otorgado_en")
    ordering = ("-otorgado_en",)
    
    def titular_email(self, obj):
        """Mask email for privacy."""
        email = obj.titular.email
        if "@" in email:
            local, domain = email.split("@")
            if len(local) > 2:
                masked_local = local[0] + "***" + local[-1]
            else:
                masked_local = "***"
            return f"{masked_local}@{domain}"
        return "***@***"
    
    titular_email.short_description = _("Titular")
    titular_email.admin_order_field = "titular__email"


class SolicitudHabeasDataAdmin(admin.ModelAdmin):
    """Admin configuration for SolicitudHabeasData."""
    list_display = (
        "titular_email",
        "tipo",
        "estado",
        "fecha_radicacion",
        "fecha_limite",
        "resuelto_en",
    )
    list_filter = ("estado", "tipo", "fecha_radicacion")
    search_fields = ("titular__email", "descripcion")
    readonly_fields = ("fecha_radicacion", "fecha_limite", "suprimido_en")
    date_hierarchy = "fecha_radicacion"
    ordering = ("-fecha_radicacion",)
    
    actions = ["responder", "rechazar"]
    
    def titular_email(self, obj):
        """Mask email for privacy."""
        email = obj.titular.email
        if "@" in email:
            local, domain = email.split("@")
            if len(local) > 2:
                masked_local = local[0] + "***" + local[-1]
            else:
                masked_local = "***"
            return f"{masked_local}@{domain}"
        return "***@***"
    
    titular_email.short_description = _("Titular")
    titular_email.admin_order_field = "titular__email"
    
    def responder(self, request, queryset):
        """Mark selected requests as resolved."""
        # This will be implemented when the transicionar service is created
        pass
    
    responder.short_description = _("Marcar como resueltas")
    
    def rechazar(self, request, queryset):
        """Mark selected requests as rejected."""
        # This will be implemented when the transicionar service is created
        pass
    
    rechazar.short_description = _("Marcar como rechazadas")


# Register the new models
admin.site.register(Consentimiento, ConsentimientoAdmin)
admin.site.register(SolicitudHabeasData, SolicitudHabeasDataAdmin)


class NotificationAdmin(admin.ModelAdmin):
    """Admin configuration for Notification."""
    
    list_display = (
        "recipient_email",
        "event",
        "tipo",
        "leido",
        "created_at",
        "repeat_count",
    )
    list_filter = ("tipo", "event", "read_at", "created_at")
    search_fields = ("recipient__email", "event", "titulo")
    readonly_fields = ("payload", "created_at", "dispatched_at", "repeat_count")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
    
    actions = ["marcar_como_leida", "reenviar_a_audit"]
    
    def recipient_email(self, obj):
        """Mask email for privacy."""
        email = obj.recipient.email
        if "@" in email:
            local, domain = email.split("@")
            if len(local) > 2:
                masked_local = local[0] + "***" + local[-1]
            else:
                masked_local = "***"
            return f"{masked_local}@{domain}"
        return "***@***"
    
    recipient_email.short_description = _("Destinatario")
    recipient_email.admin_order_field = "recipient__email"
    
    def leido(self, obj):
        """Display leido status."""
        return obj.leido
    
    leido.short_description = _("Leído")
    leido.boolean = True
    leido.admin_order_field = "read_at"
    
    def has_permission(self, request):
        """Only allow R-ADMIN and R-COORD roles."""
        if not request.user.is_authenticated:
            return False
        
        # Check if user has R-ADMIN or R-COORD role
        from apps.accounts.models import UserRole
        return UserRole.objects.filter(
            user=request.user,
            role__code__in=["R-ADMIN", "R-COORD"]
        ).exists()
    
    def has_module_permission(self, request):
        """Check module permission."""
        return self.has_permission(request)
    
    def has_view_permission(self, request, obj=None):
        """Check view permission."""
        return self.has_permission(request)
    
    def has_add_permission(self, request):
        """Notifications are created by system only."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Check change permission."""
        return self.has_permission(request)
    
    def has_delete_permission(self, request, obj=None):
        """Check delete permission."""
        return self.has_permission(request)
    
    def marcar_como_leida(self, request, queryset):
        """Mark selected notifications as read."""
        import logging
        import uuid

        from django.utils import timezone
        from apps.audit.services import log_audit_event

        logger = logging.getLogger(__name__)

        updated = queryset.filter(read_at__isnull=True).update(read_at=timezone.now())

        # Log batch audit event via the canonical helper so the
        # hash chain stays intact. ``entity_id`` is a stable UUID5
        # of the batch timestamp so the value is unique and not a
        # reference to a specific row (CHG-801 / AUD-001).
        batch_id = uuid.uuid5(
            uuid.NAMESPACE_URL,
            f"notif-batch-read:{request.user.id}:{timezone.now().isoformat()}",
        )
        try:
            log_audit_event(
                actor=request.user,
                action="notif.batch_read",
                entity="Notification",
                entity_id=batch_id,
                changes={"count": updated},
                ip_address=None,
                user_agent="",
                module="accounts",
            )
        except Exception:
            # Log loud failure; don't swallow silently (CHG-801 /
            # AUD-001 + AUD-020).
            logger.exception("audit: notif.batch_read audit log failed")

        self.message_user(request, f"{updated} notificaciones marcadas como leídas.")
    
    marcar_como_leida.short_description = _("Marcar como leídas")
    
    def reenviar_a_audit(self, request, queryset):
        """Re-dispatch selected notifications to audit."""
        from apps.accounts.services.notifications import get_notifiers
        
        notifiers = get_notifiers()
        dispatched = 0
        
        for notification in queryset:
            for notifier in notifiers:
                if hasattr(notifier, '_dispatch_notification'):
                    try:
                        notifier._dispatch_notification(notification.id)
                        dispatched += 1
                    except Exception:
                        pass  # Skip failures
        
        self.message_user(request, f"{dispatched} notificaciones reenviadas a auditoría.")
    
    reenviar_a_audit.short_description = _("Reenviar a auditoría")


# Register Notification admin
admin.site.register(Notification, NotificationAdmin)