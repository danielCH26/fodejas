"""Models for audit app."""
import hashlib
import uuid
from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    """Immutable audit log with hash chain."""

    ACTION_CHOICES = [
        ("CREATE", "Create"),
        ("UPDATE", "Update"),
        ("DELETE", "Delete"),
        ("LOGIN", "Login"),
        ("LOGOUT", "Logout"),
        ("ACCESS", "Access"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_events",
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    entity = models.CharField(max_length=100, db_index=True)
    entity_id = models.UUIDField(db_index=True)
    changes = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True, default="")
    module = models.CharField(max_length=50)
    previous_hash = models.CharField(max_length=64)
    current_hash = models.CharField(max_length=64, unique=True)
    is_valid = models.BooleanField(default=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["entity", "entity_id"]),
            models.Index(fields=["actor", "timestamp"]),
            models.Index(fields=["timestamp"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.entity} at {self.timestamp}"

    @staticmethod
    def calculate_hash(timestamp, actor_id, action, entity, entity_id, changes, previous_hash):
        """Calculate SHA-256 hash for audit record."""
        data = f"{timestamp}|{actor_id}|{action}|{entity}|{entity_id}|{changes}|{previous_hash}"
        return hashlib.sha256(data.encode()).hexdigest()

    @classmethod
    def get_previous_hash(cls):
        """Get the hash of the last record or initial hash if no records."""
        last_event = cls.objects.order_by("-timestamp").first()
        if last_event:
            return last_event.current_hash
        return "0" * 64

    def save(self, *args, **kwargs):
        """Save with automatic hash calculation."""
        if not self.previous_hash:
            self.previous_hash = self.get_previous_hash()

        if not self.current_hash:
            self.current_hash = self.calculate_hash(
                self.timestamp,
                self.actor_id if self.actor else None,
                self.action,
                self.entity,
                self.entity_id,
                self.changes,
                self.previous_hash,
            )

        super().save(*args, **kwargs)
