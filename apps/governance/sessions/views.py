"""API views for governance sessions (CHG-501, CAP-017).

Role matrix (PR #16 seeded codes):
- Management (convocar, abrir, cerrar punto, finalizar, actas,
  firmar): R-JUNTA / R-ADMIN.
- Attendance and voting: the member themselves (ownership via
  MiembroSesion.user).
- Acta read access: R-JUNTA / R-ADMIN / R-CT / R-OFIJUR.
"""

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import HasAnyRole
from apps.governance.sessions.models import (
    ActaSesion,
    MiembroSesion,
    OrdenDelDiaPunto,
    Sesion,
)
from apps.governance.sessions.serializers import (
    ActaSesionSerializer,
    SesionSerializer,
)
from apps.governance.sessions.services import SessionService

MANAGEMENT_ROLES = ["R-JUNTA", "R-ADMIN"]
ACTA_READ_ROLES = ["R-JUNTA", "R-ADMIN", "R-CT", "R-OFIJUR"]


def _management_perm():
    return HasAnyRole(MANAGEMENT_ROLES)


def _acta_read_perm():
    return HasAnyRole(ACTA_READ_ROLES)


class SesionViewSet(viewsets.ModelViewSet):
    """ViewSet for governance sessions (CHG-501)."""

    queryset = Sesion.objects.all()
    serializer_class = SesionSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), _acta_read_perm()]
        if self.action in ["votar", "declarar_conflicto", "votar_impedimento"]:
            return [IsAuthenticated()]
        return [IsAuthenticated(), _management_perm()]

    def create(self, request, *args, **kwargs):
        """Convocar una sesión (valida anticipos 5/2 días hábiles)."""
        organo = request.data.get("organo")
        tipo = request.data.get("tipo")
        fecha_hora = request.data.get("fecha_hora")
        asunto = request.data.get("asunto", "")

        if not all([organo, tipo, fecha_hora]):
            return Response(
                {"error": "organo, tipo and fecha_hora are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            sesion = SessionService.convocar_sesion(
                organo=organo,
                tipo=tipo,
                fecha_hora=fecha_hora,
                asunto=asunto,
                actor=request.user,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(SesionSerializer(sesion).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def asistencia(self, request, pk=None):
        """Register attendance for session members (management action).

        Body: {"members": [{"user_id": ..., "rol": ..., "asistencia":
        "PRESENTE|VIRTUAL|AUSENTE", "es_miembro_cargo": bool,
        "conflicto_declarado": bool}, ...]}
        """
        members = request.data.get("members")
        if not members:
            return Response({"error": "members is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            registros = SessionService.registrar_asistencia(pk, members, actor=request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"registered": len(registros)})

    @action(detail=True, methods=["post"])
    def abrir(self, request, pk=None):
        try:
            sesion = SessionService.abrir_sesion(pk, actor=request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"status": sesion.estado})

    @action(detail=True, methods=["post"])
    def votar(self, request, pk=None):
        """Vote on a punto as the CURRENT user (ownership enforced)."""
        punto_id = request.data.get("punto_id")
        valor = request.data.get("valor")
        if not punto_id or not valor:
            return Response(
                {"error": "punto_id and valor are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            punto = OrdenDelDiaPunto.objects.get(id=punto_id, sesion_id=pk)
        except OrdenDelDiaPunto.DoesNotExist:
            return Response(
                {"error": "Punto not found in this session"},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            miembro = MiembroSesion.objects.get(sesion_id=pk, user=request.user)
        except MiembroSesion.DoesNotExist:
            return Response(
                {"error": "You are not a member of this session"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            voto = SessionService.registrar_voto(
                sesion_id=pk,
                punto_id=punto.id,
                miembro_sesion_id=miembro.id,
                valor=valor,
                actor=request.user,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"valor": voto.valor})

    @action(detail=True, methods=["post"])
    def cerrar_punto(self, request, pk=None):
        punto_id = request.data.get("punto_id")
        if not punto_id:
            return Response({"error": "punto_id is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            punto = SessionService.cerrar_punto(punto_id, actor=request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"estado": punto.estado})

    @action(detail=True, methods=["post"])
    def finalizar(self, request, pk=None):
        try:
            sesion = SessionService.finalizar_sesion(pk, actor=request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"status": sesion.estado})

    @action(detail=True, methods=["post"])
    def declarar_conflicto(self, request, pk=None):
        """Declare a conflict of interest on a punto (self-service)."""
        punto_id = request.data.get("punto_id")
        texto = request.data.get("texto", "")
        if not punto_id or not texto.strip():
            return Response(
                {"error": "punto_id and texto are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            miembro = MiembroSesion.objects.get(sesion_id=pk, user=request.user)
        except MiembroSesion.DoesNotExist:
            return Response(
                {"error": "You are not a member of this session"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            declaracion = SessionService.declarar_conflicto(
                pk, punto_id, miembro.id, texto, actor=request.user
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "id": str(declaracion.id),
                "estado": declaracion.estado,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def votar_impedimento(self, request, pk=None):
        """Vote on another member's conflict impediment (majority resolves)."""
        declaracion_id = request.data.get("declaracion_id")
        a_favor = request.data.get("a_favor")
        if not declaracion_id or a_favor is None:
            return Response(
                {"error": "declaracion_id and a_favor are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            miembro = MiembroSesion.objects.get(sesion_id=pk, user=request.user)
        except MiembroSesion.DoesNotExist:
            return Response(
                {"error": "You are not a member of this session"},
                status=status.HTTP_403_FORBIDDEN,
            )
        try:
            declaracion = SessionService.votar_impedimento(
                declaracion_id, miembro.id, bool(a_favor), actor=request.user
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"estado": declaracion.estado})

    @action(detail=True, methods=["post"])
    def generar_acta(self, request, pk=None):
        try:
            acta = SessionService.generar_acta(pk, actor=request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except RuntimeError as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(ActaSesionSerializer(acta).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def firmar_acta(self, request, pk=None):
        firmantes = request.data.get("firmantes")
        if not firmantes:
            return Response({"error": "firmantes is required"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            acta = SessionService.firmar_acta(pk, firmantes, actor=request.user)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ActaSesionSerializer(acta).data)


class ActaViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only access to signed session actas."""

    queryset = ActaSesion.objects.all()
    serializer_class = ActaSesionSerializer

    def get_permissions(self):
        return [IsAuthenticated(), _acta_read_perm()]
