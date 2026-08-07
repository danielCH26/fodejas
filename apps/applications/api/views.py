"""API views for applications."""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.applications.models import Anexo, Solicitud
from apps.applications.api.serializers import (
    AnexoSerializer,
    SolicitudSerializer,
    SolicitudCreateSerializer,
    SolicitudSubmitSerializer,
)
from apps.applications.services import save_draft, submit
from apps.accounts.permissions import HasRole, HasAnyRole, IsAdminOrHasRole


class SolicitudViewSet(viewsets.ModelViewSet):
    """ViewSet for Solicitud CRUD."""

    queryset = Solicitud.objects.all()
    serializer_class = SolicitudSerializer

    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ["list", "retrieve"]:
            # Aspirantes see their own, rev/comite/admin see all
            return [IsAuthenticated()]
        elif self.action in ["create"]:
            # Aspirantes can create solicitudes
            return [IsAdminOrHasRole('R-ASPIRANTE')]
        elif self.action in ["update", "partial_update"]:
            # Aspirantes can update their own drafts
            return [IsAuthenticated()]
        elif self.action in ["destroy"]:
            # Only own drafts can be destroyed
            return [IsAuthenticated()]
        elif self.action in ["submit"]:
            # Aspirantes can submit
            return [IsAdminOrHasRole('R-ASPIRANTE')]
        return [IsAuthenticated()]

    def get_queryset(self):
        """Filter based on user roles."""
        user = self.request.user
        
        # Admin and revisor can see all
        if user.is_superuser or user.is_staff:
            return Solicitud.objects.all()
        
        # Check for internal roles
        if user.user_roles.filter(role__code__in=['R-ADMIN', 'R-REVISOR', 'R-COMITE', 'R-COORDINADOR']).exists():
            return Solicitud.objects.all()
        
        # Aspirantes see only their own
        return Solicitud.objects.filter(aspirante=user)

    def create(self, request, *args, **kwargs):
        """Create a new draft solicitud."""
        serializer = SolicitudCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get convocatoria
        from apps.convocatories.models import Convocatory

        try:
            convocatoria = Convocatory.objects.get(
                pk=serializer.validated_data["convocatoria_id"]
            )
        except Convocatory.DoesNotExist:
            return Response(
                {"error": "Convocatoria no encontrada"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check if user already has application for this convocation
        if Solicitud.objects.filter(
            convocatoria=convocatoria,
            aspirante=request.user
        ).exists():
            return Response(
                {"error": "Ya tienes una solicitud para esta convocatoria"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Create draft
        solicitud = Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=request.user,
            estado=Solicitud.Estado.BORRADOR,
        )

        return Response(
            SolicitudSerializer(solicitud).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def save_draft(self, request, pk=None):
        """Save draft data for current step."""
        solicitud = self.get_object()
        step = request.data.get("step", solicitud.current_step)
        data = request.data.get("data", {})

        try:
            save_draft(solicitud, step, data)
            return Response({"status": "draft saved"})
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def submit_fui(self, request, pk=None):
        """Submit completed FUI."""
        serializer = SolicitudSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        solicitud = self.get_object()

        try:
            submit(
                solicitud,
                consentimiento=serializer.validated_data["consentimiento"],
                actor=request.user,
            )
            return Response(
                {"status": "submitted", "radicado": solicitud.radicado}
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
