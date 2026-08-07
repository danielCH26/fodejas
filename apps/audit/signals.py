"""Audit signals for automatic logging."""
import uuid
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from apps.accounts.models import CustomUser, Role, Permission
from .services import log_audit_event


def get_request_info(request):
    """Extract request info for audit logging."""
    if request is None:
        return None, None

    ip_address = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:500]
    return ip_address, user_agent


def get_client_ip(request):
    """Get client IP from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


# Models to audit
AUDIT_MODELS = [
    (CustomUser, "accounts"),
    (Role, "accounts"),
    (Permission, "accounts"),
    # Core domain catalogs
    ("apps.core.models.Estrato", "core"),
    ("apps.core.models.GrupoSisben", "core"),
    ("apps.core.models.Etnia", "core"),
    ("apps.core.models.MunicipioIsla", "core"),
    ("apps.core.models.NivelFormacion", "core"),
    ("apps.core.models.ModalidadApoyo", "core"),
    ("apps.core.models.TipoIes", "core"),
    ("apps.core.models.TipoDocumento", "core"),
    ("apps.core.models.EstadoDocumento", "core"),
    ("apps.core.models.CausalTerminacionConvenio", "core"),
    # Convocatories (CHG-104)
    ("apps.convocatories.models.Convocatory", "convocatories"),
    ("apps.convocatories.models.ConfiguracionConvocatoria", "convocatories"),
    ("apps.convocatories.models.Hito", "convocatories"),
    ("apps.convocatories.models.Cupo", "convocatories"),
    ("apps.convocatories.models.ConvocatoriaVersion", "convocatories"),
]


def register_audit_signals():
    """Register audit signals for all models."""
    for model, module in AUDIT_MODELS:
        post_save.connect(audit_save_receiver, sender=model)
        post_delete.connect(audit_delete_receiver, sender=model)


@receiver(post_save)
def audit_save_receiver(sender, instance, created, **kwargs):
    """Log model create/update events."""
    # Skip if not one of our audited models
    if sender not in [m[0] for m in AUDIT_MODELS]:
        return

    # Get module name
    module = sender._meta.app_label

    action = "CREATE" if created else "UPDATE"

    # Get changes for updates
    changes = None
    if not created:
        # For updates, we could track changed fields
        # For now, just log that an update happened
        changes = {"updated": True}

    try:
        log_audit_event(
            actor=None,  # Would need to get from request context
            action=action,
            entity=sender._meta.model_name,
            entity_id=instance.id,
            changes=changes,
            module=module,
        )
    except Exception:
        # Don't let audit failures break the main operation
        pass


@receiver(post_delete)
def audit_delete_receiver(sender, instance, **kwargs):
    """Log model delete events."""
    # Skip if not one of our audited models
    if sender not in [m[0] for m in AUDIT_MODELS]:
        return

    module = sender._meta.app_label

    try:
        log_audit_event(
            actor=None,
            action="DELETE",
            entity=sender._meta.model_name,
            entity_id=instance.id,
            changes={"deleted": True},
            module=module,
        )
    except Exception:
        pass
