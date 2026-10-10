"""API views for Convocatory."""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsAdminOrHasRole
from apps.convocatories.api.serializers import (
    ConvocatorySerializer,
    TransitionSerializer,
)
from apps.convocatories.models import Convocatory
from apps.convocatories.services import convocatoria_service


class ConvocatoryViewSet(viewsets.ModelViewSet):
    """ViewSet for Convocatory CRUD and transitions."""

    queryset = Convocatory.objects.all()
    serializer_class = ConvocatorySerializer

    def get_authenticators(self):
        """Remove authentication for public endpoints."""
        # Check request method for safe methods
        if self.request.method in ["GET", "HEAD", "OPTIONS"]:
            return []
        return super().get_authenticators()

    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action in ["list", "retrieve"]:
            # Allow unauthenticated to view public convocation info
            return [AllowAny()]
        elif self.action in ["create"]:
            # Only admins and coordinators can create
            return [IsAdminOrHasRole("R-ADMIN"), IsAdminOrHasRole("R-COORDINADOR")]
        elif self.action in ["update", "partial_update", "destroy"]:
            # Only admins and coordinators can modify
            return [IsAdminOrHasRole("R-ADMIN"), IsAdminOrHasRole("R-COORDINADOR")]
        elif self.action in ["transicionar"]:
            # Only admins, coordinators and committee can transition
            return [
                IsAdminOrHasRole("R-ADMIN"),
                IsAdminOrHasRole("R-COORDINADOR"),
                IsAdminOrHasRole("R-COMITE"),
            ]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        """Use TransitionSerializer for transicionar action."""
        if self.action == "transicionar":
            return TransitionSerializer
        return ConvocatorySerializer

    @action(detail=True, methods=["post"])
    def transicionar(self, request, pk=None):
        """Execute a state transition."""
        convocatoria = self.get_object()
        serializer = TransitionSerializer(
            data=request.data,
            instance=convocatoria,
        )

        if serializer.is_valid():
            try:
                convocatoria_service.transicionar_estado(
                    convocatoria=convocatoria,
                    estado_destino=serializer.validated_data["destino"],
                    actor=request.user,
                    motivo=serializer.validated_data.get("motivo", ""),
                )

                return Response(
                    {"status": " transición exitosa", "estado": convocatoria.estado},
                    status=status.HTTP_200_OK,
                )

            except Exception as e:
                return Response(
                    {"error": str(e)},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def publicar(self, request, pk=None):
        """Publish a convocation (shortcut)."""
        convocatoria = self.get_object()

        try:
            convocatoria_service.publicar(convocatoria, request.user)
            return Response(
                {"status": "publicada", "estado": convocatoria.estado},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def cerrar(self, request, pk=None):
        """Close a convocation (shortcut)."""
        convocatoria = self.get_object()

        try:
            convocatoria_service.cerrar(convocatoria, request.user)
            return Response(
                {"status": "cerrada", "estado": convocatoria.estado},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

    @action(detail=True, methods=["post"])
    def cancelar(self, request, pk=None):
        """Cancel a convocation (shortcut)."""
        convocatoria = self.get_object()
        motivo = request.data.get("motivo", "")

        try:
            convocatoria_service.cancelar(convocatoria, request.user, motivo)
            return Response(
                {"status": "cancelada", "estado": convocatoria.estado},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )
