"""Views for audit app."""
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, generics, permissions
from rest_framework.response import Response

from .models import AuditEvent
from .serializers import AuditChainVerifySerializer, AuditEventSerializer
from .services import verify_chain


class AuditEventListView(generics.ListAPIView):
    """List audit events with filters."""

    queryset = AuditEvent.objects.all()
    serializer_class = AuditEventSerializer
    permission_classes = [permissions.IsAuthenticated]

    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    filterset_fields = {
        "actor": ["exact"],
        "action": ["exact"],
        "entity": ["exact"],
        "entity_id": ["exact"],
        "module": ["exact"],
        "timestamp": ["gte", "lte", "exact"],
    }

    search_fields = ["entity", "module"]
    ordering_fields = ["timestamp", "action", "entity"]
    ordering = ["-timestamp"]


class AuditEventDetailView(generics.RetrieveAPIView):
    """Retrieve a single audit event."""

    queryset = AuditEvent.objects.all()
    serializer_class = AuditEventSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = "id"


class AuditChainVerifyView(generics.RetrieveAPIView):
    """Verify the integrity of the audit chain."""

    permission_classes = [permissions.IsAdminUser]
    serializer_class = AuditChainVerifySerializer

    def retrieve(self, request, *args, **kwargs):
        """Verify the audit chain."""
        result = verify_chain()
        return Response(result)
