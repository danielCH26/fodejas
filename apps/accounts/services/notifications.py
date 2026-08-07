"""Notification services for accounts app."""
import logging
from typing import Protocol
from django.db import transaction
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.accounts.models import Notification
from apps.audit.models import AuditEvent

logger = logging.getLogger(__name__)
CustomUser = get_user_model()


class NotificationPort(Protocol):
    """Protocol for notification adapters."""
    
    def notify(self, user: CustomUser, event: str, payload: dict) -> Notification:
        """Send a notification to a user."""
        ...
    
    def mark_read(self, notification: Notification, user: CustomUser) -> None:
        """Mark a notification as read."""
        ...


# Global registry for notifiers
NOTIFIERS: list[NotificationPort] = []


def get_notifiers() -> list[NotificationPort]:
    """Get the list of registered notifiers."""
    return NOTIFIERS


class InAppNotifier:
    """In-app notification adapter."""
    
    def notify(self, user: CustomUser, event: str, payload: dict) -> Notification:
        """
        Send an in-app notification.
        
        Args:
            user: The recipient user
            event: Event code (e.g., 'habeas.created')
            payload: Notification payload (PII should be masked)
            
        Returns:
            The created or updated Notification instance
        """
        # Simplified payload - skipping mask_pii per user instructions
        safe_payload = self._sanitize_payload(payload)
        
        # Determine notification type based on event
        tipo = self._determine_tipo(event)
        
        # Generate title and message
        titulo, mensaje = self._generate_content(event, safe_payload)
        
        with transaction.atomic():
            today = timezone.now().date()
            
            # Idempotent upsert: only one notification per (user, event, day)
            obj, created = Notification.objects.select_for_update().get_or_create(
                recipient=user,
                event=event,
                created_date=today,
                defaults={
                    "tipo": tipo,
                    "titulo": titulo,
                    "mensaje": mensaje,
                    "payload": safe_payload,
                    "repeat_count": 1,
                },
            )
            
            if not created:
                # Increment repeat count for duplicate event on same day
                obj.repeat_count += 1
                obj.save(update_fields=["repeat_count", "dispatched_at"])
            
            # Log to audit - simplified without Celery
            try:
                self._log_audit_event(
                    action="notification.created",
                    entity="Notification",
                    entity_id=obj.id,
                    user=user,
                    changes={"event": event, "tipo": tipo},
                )
                
                # Dispatch synchronously (skip Celery per user instructions)
                self._dispatch_notification(obj.id)
                
            except Exception as e:
                logger.error(f"Failed to audit/dispatch notification {obj.id}: {e}")
                # Still return the notification even if audit/dispatch fails
            
            return obj
    
    def mark_read(self, notification: Notification, user: CustomUser) -> None:
        """
        Mark a notification as read.
        
        Args:
            notification: The notification to mark as read
            user: The user marking the notification as read
        """
        if notification.recipient != user:
            raise PermissionError("User cannot mark another user's notification as read")
        
        if notification.read_at is None:
            notification.read_at = timezone.now()
            notification.save(update_fields=["read_at"])
            
            # Log to audit
            try:
                self._log_audit_event(
                    action="notification.read",
                    entity="Notification",
                    entity_id=notification.id,
                    user=user,
                    changes={"read_at": str(notification.read_at)},
                )
            except Exception as e:
                logger.error(f"Failed to audit read event for notification {notification.id}: {e}")
    
    def _sanitize_payload(self, payload: dict) -> dict:
        """Sanitize payload - simplified version without mask_pii."""
        # For now, just return the payload as-is
        # In a real implementation, this would mask PII
        return payload.copy() if payload else {}
    
    def _determine_tipo(self, event: str) -> str:
        """Determine notification type based on event."""
        if any(x in event for x in ["error", "failed", "reject", "deny"]):
            return "error"
        elif any(x in event for x in ["success", "approved", "accepted"]):
            return "success"
        elif any(x in event for x in ["warning", "alert", "expire"]):
            return "warning"
        else:
            return "info"
    
    def _generate_content(self, event: str, payload: dict) -> tuple[str, str]:
        """Generate title and message based on event and payload."""
        # Simple mapping for common events
        event_titles = {
            "habeas.created": "Solicitud de Habeas Data creada",
            "habeas.updated": "Solicitud de Habeas Data actualizada",
            "habeas.resolved": "Solicitud de Habeas Data resuelta",
            "habeas.rejected": "Solicitud de Habeas Data rechazada",
            "application.submitted": "Postulación enviada",
            "application.approved": "Postulación aprobada",
            "application.rejected": "Postulación rechazada",
        }
        
        event_messages = {
            "habeas.created": "Se ha creado una nueva solicitud de Habeas Data.",
            "habeas.updated": "Se ha actualizado una solicitud de Habeas Data.",
            "habeas.resolved": "Su solicitud de Habeas Data ha sido resuelta.",
            "habeas.rejected": "Su solicitud de Habeas Data ha sido rechazada.",
            "application.submitted": "Su postulación ha sido enviada exitosamente.",
            "application.approved": "¡Felicidades! Su postulación ha sido aprobada.",
            "application.rejected": "Su postulación no ha sido aprobada en esta convocatoria.",
        }
        
        titulo = event_titles.get(event, f"Evento: {event}")
        mensaje = event_messages.get(event, f"Evento: {event}")
        
        # Add payload context if available
        if payload:
            mensaje += f"\n\nContexto: {str(payload)[:200]}..."
        
        return titulo, mensaje
    
    def _log_audit_event(self, action: str, entity: str, entity_id, user: CustomUser, changes: dict = None):
        """Log an audit event - simplified version."""
        try:
            # Use shorter action names to fit in 20 chars
            short_action = action.replace("notification.", "notif.")
            if len(short_action) > 20:
                short_action = short_action[:20]
            
            AuditEvent.objects.create(
                actor=user,
                action=short_action,
                entity=entity,
                entity_id=entity_id,
                changes=changes or {},
                ip_address=None,  # Would get from request in real implementation
                user_agent="",
                module="accounts",
            )
        except Exception as e:
            logger.error(f"Failed to create audit event: {e}")
            # Don't fail notification creation if audit fails
    
    def _dispatch_notification(self, notification_id):
        """Dispatch notification synchronously - simplified without Celery."""
        try:
            notification = Notification.objects.get(id=notification_id)
            
            if notification.dispatched_at is None:
                notification.dispatched_at = timezone.now()
                notification.save(update_fields=["dispatched_at"])
                
                # Log dispatch to audit
                self._log_audit_event(
                    action="notification.dispatched",
                    entity="Notification",
                    entity_id=notification_id,
                    user=notification.recipient,
                    changes={"dispatched_at": str(notification.dispatched_at)},
                )
        except Notification.DoesNotExist:
            logger.error(f"Notification {notification_id} not found for dispatch")
        except Exception as e:
            logger.error(f"Failed to dispatch notification {notification_id}: {e}")
            # Log dispatch failure
            try:
                self._log_audit_event(
                    action="notif.dispatch_failed",
                    entity="Notification",
                    entity_id=notification_id,
                    user=None,
                    changes={"error": str(e)},
                )
            except Exception:
                pass  # Ignore audit failure on dispatch failure