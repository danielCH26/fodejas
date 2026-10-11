"""Models for audit app."""

import hashlib
import json
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
        ("ELECTRONIC_SIGNATURE", "Electronic Signature"),
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
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
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
        """Calculate SHA-256 hash for audit record.

        Mirrors ``apps.audit.services.calculate_hash`` so any code path
        that uses the model-level helper produces the same digest as
        the service-level helper. ``changes`` is canonicalized via
        ``json.dumps(sort_keys=True)`` to avoid Python's
        ``str(dict)`` order-sensitive repr causing a hash mismatch
        between write and verify.

        NOTE: this method is called by ``services.log_audit_event``
        AFTER the row has been inserted (so the timestamp reflects the
        stored ``auto_now_add`` value). The model's ``save()`` does
        NOT call this — see comment there.
        """
        if changes is None:
            changes_str = "null"
        else:
            changes_str = json.dumps(changes, sort_keys=True, default=str)
        data = (
            f"{timestamp}|{actor_id}|{action}|{entity}|"
            f"{entity_id}|{changes_str}|{previous_hash}"
        )
        return hashlib.sha256(data.encode()).hexdigest()

    @classmethod
    def get_previous_hash(cls):
        """Get the hash of the last record or initial hash if no records."""
        last_event = cls.objects.order_by("-timestamp").first()
        if last_event:
            return last_event.current_hash
        return "0" * 64

    def save(self, *args, **kwargs):
        """Save the audit event.

        **This method does NOT compute ``current_hash``.**

        The hash computation requires the ``timestamp`` field to be
        stamped by Django's ``auto_now_add`` (``Field.pre_save``). That
        stamp runs INSIDE ``Model.save_base``, which is invoked by
        ``super().save()``. If we tried to compute the hash here we
        would use ``self.timestamp = None`` and persist an unverifiable
        row. Instead, the canonical write path is
        ``apps.audit.services.log_audit_event``, which:
          1. Inserts the row without ``current_hash`` (relying on
             ``auto_now_add`` to stamp ``timestamp`` and ``super().save()``
             to INSERT).
          2. Reads the persisted event back so ``event.timestamp`` is the
             stamped value.
          3. Computes ``current_hash`` and persists it via a second
             ``save(update_fields=["current_hash"])``.

        ``previous_hash`` MUST be set before this method is called;
        callers obtain it via ``AuditEvent.get_previous_hash()`` or
        pass it explicitly through ``log_audit_event``.
        """
        if not self.previous_hash:
            raise ValueError(
                "AuditEvent.save() requires previous_hash to be set "
                "before insertion. Use apps.audit.services.log_audit_event."
            )
        super().save(*args, **kwargs)
