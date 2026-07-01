from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.audit"
    verbose_name = "Audit"

    def ready(self):
        """Register signals when app is ready."""
        # Import signals module to connect @receiver decorators
        import apps.audit.signals  # noqa: F401
