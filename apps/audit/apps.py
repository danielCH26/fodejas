from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit"

    def ready(self):
        """Register signals when app is ready.

        Two things happen here:

        1. ``import apps.audit.signals`` runs the module so the
           module-level ``@receiver`` decorators on
           ``audit_save_receiver`` / ``audit_delete_receiver``
           attach themselves to the unconnected ``post_save`` /
           ``post_delete`` signals.

        2. ``register_audit_signals()`` explicitly connects those
           receivers to ``post_save`` / ``post_delete`` for every
           model listed in ``AUDIT_MODELS`` (CHG-801 / AUD-010).

        The explicit registration is what makes the audit chain
        actually fire — the bare ``@receiver`` decorators only
        listen for *every* sender, which on a busy project is
        wasteful and would never match the model we want because the
        filter is checked inside the receiver body.
        """
        import apps.audit.signals  # noqa: F401

        apps.audit.signals.register_audit_signals()
