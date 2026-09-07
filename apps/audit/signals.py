"""Audit signals for automatic logging (CAP-022 / CHG-801).

``AUDIT_MODELS`` is keyed on the **model class** (not a string
label) so the ``sender`` argument of a Django signal can be compared
with class identity (``sender is ModelClass``). String keys were
broken at runtime: ``sender`` is always a class object, so
``sender in ["apps.core.models.Estrato", ...]`` always evaluated to
``False`` and the receivers never fired (AUD-010 / CHG-801).

Note: the ``audit_save_receiver`` / ``audit_delete_receiver``
functions are **not** decorated with ``@receiver(...)``. They are
connected explicitly by ``register_audit_signals()`` for each model
in ``AUDIT_MODELS``. Using ``@receiver(post_save)`` without a
``sender`` would also catch every model save in the project and
double-fire for the audited ones, polluting the chain.
"""
import logging

from django.apps import apps as django_apps
from django.db.models.signals import post_delete, post_save

from apps.core.logging_config import get_actor
from .services import log_audit_event

logger = logging.getLogger(__name__)


def get_request_info(request):
    """Extract request info for audit logging (kept for backward compatibility)."""
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


def _resolve_model(label: str):
    """Resolve a dotted label to its model class.

    Accepts both ``app_label.ModelName`` (Django's canonical form,
    e.g. ``core.Estrato``) and the full Python path
    ``apps.core.models.Estrato`` (used in the source tree). The
    full path is rewritten to ``core.Estrato`` before being passed
    to ``django_apps.get_model``.
    """
    if label.startswith("apps."):
        # Rewrite ``apps.<app_label>.models.<ModelName>`` to
        # ``<app_label>.<ModelName>`` so Django's app registry can
        # resolve it without a manual import.
        parts = label.split(".")
        if len(parts) == 4 and parts[2] == "models":
            label = f"{parts[1]}.{parts[3]}"
    return django_apps.get_model(label)


# Models to audit. Keyed by class (not string) so the receiver can
# compare with ``sender is ModelClass``. The second element of each
# tuple is the module label stored on the audit event.
AUDIT_MODELS: list[tuple[str, str]] = [
    # Accounts
    ("apps.accounts.models.CustomUser", "accounts"),
    ("apps.accounts.models.Role", "accounts"),
    ("apps.accounts.models.Permission", "accounts"),
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


def _audited_models():
    """Return the resolved ``(class, module)`` pairs.

    Resolved lazily because the app registry may not be ready when
    this module is first imported. Failures are logged and the
    offending entry is skipped — never raises during import.
    """
    resolved: list[tuple[type, str]] = []
    for entry in AUDIT_MODELS:
        label, module = entry
        try:
            model_cls = _resolve_model(label) if isinstance(label, str) else label
        except LookupError:
            logger.warning("audit: model %s not found in app registry", label)
            continue
        resolved.append((model_cls, module))
    return resolved


def register_audit_signals() -> None:
    """Connect audit receivers to ``post_save`` / ``post_delete``.

    Called from ``apps.audit.apps.AuditConfig.ready()`` once the
    app registry is populated. Iterating over the resolved model
    classes (rather than string labels) means Django's signal
    dispatcher does the class-identity match, which is exactly
    what we need.
    """
    for model_cls, _module in _audited_models():
        post_save.connect(audit_save_receiver, sender=model_cls)
        post_delete.connect(audit_delete_receiver, sender=model_cls)


def audit_save_receiver(sender, instance, created, **kwargs):
    """Log model create/update events for audited models."""
    # Skip models we are not auditing. Use class identity (`is`), not
    # equality — subclasses should not trigger an audit event for the
    # parent class.
    if not any(sender is m[0] for m in _audited_models()):
        return

    module = sender._meta.app_label
    action = "CREATE" if created else "UPDATE"

    # The helper stamps ``actor_is_system=True`` onto ``changes``
    # when ``actor is None``. We always pass a dict so the
    # sentinel survives the round-trip into JSON storage.
    changes = {"updated": False} if created else {"updated": True}

    actor = get_actor()
    try:
        log_audit_event(
            actor=actor,
            action=action,
            entity=sender._meta.model_name,
            entity_id=instance.id,
            changes=changes,
            module=module,
        )
    except Exception:
        # Log the failure with structured context; never let an
        # audit failure abort the user's save (CHG-801 / AUD-002).
        logger.exception(
            "audit: post_save handler failed",
            extra={
                "sender": sender.__name__,
                "instance_id": getattr(instance, "id", None),
            },
        )


def audit_delete_receiver(sender, instance, **kwargs):
    """Log model delete events for audited models."""
    if not any(sender is m[0] for m in _audited_models()):
        return

    module = sender._meta.app_label
    actor = get_actor()
    try:
        log_audit_event(
            actor=actor,
            action="DELETE",
            entity=sender._meta.model_name,
            entity_id=instance.id,
            changes={"deleted": True, "actor_is_system": actor is None},
            module=module,
        )
    except Exception:
        logger.exception(
            "audit: post_delete handler failed",
            extra={
                "sender": sender.__name__,
                "instance_id": getattr(instance, "id", None),
            },
        )