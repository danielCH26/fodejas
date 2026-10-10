"""Views for accounts API."""
from django.utils.translation import gettext_lazy as _
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.api.serializers import (
    ConsentimientoSerializer,
    NotificationSerializer,
    SolicitudHabeasDataCreateSerializer,
    SolicitudHabeasDataSerializer,
    SolicitudHabeasDataUpdateSerializer,
)
from apps.accounts.models import Consentimiento, Notification, SolicitudHabeasData, UserRole
from apps.accounts.permissions import IsAdminOrHasRole


class ConsentimientoViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Consentimiento model."""

    queryset = Consentimiento.objects.select_related("titular").order_by("-otorgado_en")
    serializer_class = ConsentimientoSerializer
    permission_classes = [IsAdminOrHasRole('R-ADMIN')]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["tipo", "revocado_en"]
    search_fields = ["titular__email", "version_etiqueta"]
    ordering_fields = ["otorgado_en", "revocado_en"]
    ordering = ["-otorgado_en"]


class SolicitudHabeasDataViewSet(viewsets.ModelViewSet):
    """ViewSet for SolicitudHabeasData model."""

    queryset = SolicitudHabeasData.objects.select_related("titular", "resuelto_por").order_by("-fecha_radicacion")
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["tipo", "estado"]
    search_fields = ["titular__email", "descripcion"]
    ordering_fields = ["fecha_radicacion", "fecha_limite", "resuelto_en"]
    ordering = ["-fecha_radicacion"]

    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ["list", "retrieve"]:
            # Admin users or users with R-ADMIN role can list/retrieve all
            return [IsAdminOrHasRole('R-ADMIN')]
        elif self.action in ["create"]:
            # Authenticated users can create requests
            return [IsAuthenticated()]
        elif self.action in ["update", "partial_update", "destroy"]:
            # Admin users or users with R-ADMIN role can update
            return [IsAdminOrHasRole('R-ADMIN')]
        return [IsAdminOrHasRole('R-ADMIN')]

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == "create":
            return SolicitudHabeasDataCreateSerializer
        elif self.action in ["update", "partial_update"]:
            return SolicitudHabeasDataUpdateSerializer
        return SolicitudHabeasDataSerializer

    def get_queryset(self):
        """Filter queryset based on user permissions."""
        if self.request.user.is_staff:
            # Admin users can see all requests
            return self.queryset
        else:
            # Regular users can only see their own requests
            return self.queryset.filter(titular=self.request.user)

    def create(self, request, *args, **kwargs):
        """Create a new solicitud."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Check that user is creating request for themselves
        if request.user != serializer.validated_data.get("titular", request.user):
            return Response(
                {"detail": _("No puedes crear solicitudes para otros usuarios.")},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        # Send notification for new habeas data request
        from apps.accounts.services.notifications import get_notifiers
        notifiers = get_notifiers()
        solicitud = serializer.instance

        for notifier in notifiers:
            notifier.notify(
                user=solicitud.titular,
                event="habeas.created",
                payload={
                    "solicitud_id": str(solicitud.id),
                    "tipo": solicitud.tipo,
                    "descripcion": solicitud.descripcion[:100],  # Truncate
                },
            )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )

    def update(self, request, *args, **kwargs):
        """Update a solicitud (admin only)."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=False)
        serializer.is_valid(raise_exception=True)

        # Check if state is being changed
        if "estado" in serializer.validated_data:
            old_estado = instance.estado
            new_estado = serializer.validated_data["estado"]

            # Validate state transition
            valid_transitions = {
                "radicada": ["en_tramite", "rechazada", "vencida"],
                "en_tramite": ["resuelta", "rechazada", "vencida"],
                "resuelta": [],
                "rechazada": [],
                "vencida": [],
            }

            if old_estado in valid_transitions and new_estado not in valid_transitions[old_estado]:
                return Response(
                    {"detail": _("Transición de estado no válida.")},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Set resolver info if being resolved or rejected
            if new_estado in ["resuelta", "rechazada"]:
                serializer.validated_data["resuelto_por"] = request.user
                serializer.validated_data["resuelto_en"] = request.user.last_activity

        self.perform_update(serializer)

        # Send notification for updated habeas data request
        from apps.accounts.services.notifications import get_notifiers
        notifiers = get_notifiers()
        solicitud = serializer.instance

        # Determine event based on new state
        if "estado" in serializer.validated_data:
            new_estado = serializer.validated_data["estado"]
            if new_estado == "resuelta":
                event = "habeas.resolved"
            elif new_estado == "rechazada":
                event = "habeas.rejected"
            elif new_estado == "en_tramite":
                event = "habeas.updated"
            else:
                event = "habeas.updated"

            for notifier in notifiers:
                notifier.notify(
                    user=solicitud.titular,
                    event=event,
                    payload={
                        "solicitud_id": str(solicitud.id),
                        "estado": new_estado,
                        "tipo": solicitud.tipo,
                    },
                )

        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def responder(self, request, pk=None):
        """Mark a solicitud as resolved."""
        instance = self.get_object()

        if instance.estado not in ["radicada", "en_tramite"]:
            return Response(
                {"detail": _("Solo las solicitudes radicadas o en trámite pueden ser resueltas.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        respuesta = request.data.get("respuesta")
        evidencia_url = request.data.get("evidencia_url")

        if not respuesta:
            return Response(
                {"respuesta": _("La respuesta es obligatoria.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the instance
        instance.estado = "resuelta"
        instance.respuesta = respuesta
        instance.evidencia_url = evidencia_url
        instance.resuelto_por = request.user
        instance.resuelto_en = request.user.last_activity
        instance.save()

        # Send notification for resolved habeas data request
        from apps.accounts.services.notifications import get_notifiers
        notifiers = get_notifiers()

        for notifier in notifiers:
            notifier.notify(
                user=instance.titular,
                event="habeas.resolved",
                payload={
                    "solicitud_id": str(instance.id),
                    "estado": "resuelta",
                    "tipo": instance.tipo,
                    "respuesta": instance.respuesta[:100] if instance.respuesta else "",  # Truncate
                },
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAdminUser])
    def rechazar(self, request, pk=None):
        """Mark a solicitud as rejected."""
        instance = self.get_object()

        if instance.estado not in ["radicada", "en_tramite"]:
            return Response(
                {"detail": _("Solo las solicitudes radicadas o en trámite pueden ser rechazadas.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        motivo = request.data.get("motivo")

        if not motivo:
            return Response(
                {"motivo": _("El motivo es obligatorio.")},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update the instance
        instance.estado = "rechazada"
        instance.motivo_rechazo = motivo
        instance.resuelto_por = request.user
        instance.resuelto_en = request.user.last_activity
        instance.save()

        # Send notification for rejected habeas data request
        from apps.accounts.services.notifications import get_notifiers
        notifiers = get_notifiers()

        for notifier in notifiers:
            notifier.notify(
                user=instance.titular,
                event="habeas.rejected",
                payload={
                    "solicitud_id": str(instance.id),
                    "estado": "rechazada",
                    "tipo": instance.tipo,
                    "motivo": instance.motivo_rechazo[:100] if instance.motivo_rechazo else "",  # Truncate
                },
            )

        serializer = self.get_serializer(instance)
        return Response(serializer.data)

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for Notification model."""

    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["tipo", "leido"]
    ordering_fields = ["created_at", "read_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        """Return notifications for the current user only."""
        return Notification.objects.filter(recipient=self.request.user)

    @action(detail=True, methods=["post"])
    def read(self, request, pk=None):
        """Mark a notification as read."""
        notification = self.get_object()

        # Check ownership
        if notification.recipient != request.user:
            return Response(
                {"detail": _("No tienes permiso para marcar esta notificación como leída.")},
                status=status.HTTP_403_FORBIDDEN
            )

        # Mark as read
        from apps.accounts.services.notifications import get_notifiers
        notifiers = get_notifiers()
        for notifier in notifiers:
            notifier.mark_read(notification, request.user)

        # Refresh from database
        notification.refresh_from_db()
        serializer = self.get_serializer(notification)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def read_all(self, request):
        """Mark all unread notifications as read."""
        unread_notifications = self.get_queryset().filter(read_at__isnull=True)

        # Mark each as read
        from apps.accounts.services.notifications import get_notifiers
        notifiers = get_notifiers()
        updated_count = 0

        for notification in unread_notifications:
            for notifier in notifiers:
                try:
                    notifier.mark_read(notification, request.user)
                    updated_count += 1
                except Exception:
                    # Skip individual failures
                    pass

        return Response({"updated": updated_count})

    @action(detail=False, methods=["get"])
    def unread_count(self, request):
        """Get count of unread notifications."""
        unread_count = self.get_queryset().filter(read_at__isnull=True).count()
        return Response({"unread": unread_count})


class MeView(APIView):
    """GET /api/auth/me/ — return authenticated user with roles (JSON).

    Reuses the payload shape from accounts_views.CurrentUserAPIView.
    Test: apps.accounts.tests.test_jwt.JWTUserRolesTests.test_user_info_includes_roles.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Handle GET — return JSON user payload with roles."""
        from django.http import JsonResponse

        user = request.user
        roles = list(
            UserRole.objects.filter(user=user)
            .select_related("role")
            .values("role__code", "role__name", "role__type")
        )

        return JsonResponse({
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "documento": user.documento,
            "roles": [
                {
                    "code": r["role__code"],
                    "name": r["role__name"],
                    "type": r["role__type"],
                }
                for r in roles
            ],
        })
