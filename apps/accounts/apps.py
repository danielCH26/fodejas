from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Accounts"
    
    def ready(self):
        """Initialize the application."""
        # Import here to avoid circular imports
        from apps.accounts.services.notifications import NOTIFIERS, InAppNotifier
        
        # Register the InAppNotifier as the default notification adapter
        NOTIFIERS.append(InAppNotifier())
        
        # Import and connect signals
        from . import signals  # noqa
