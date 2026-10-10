"""Services for claims (CHG-205) and appeals (CHG-206)."""

from django.utils import timezone

from apps.claims.domain.transitions import (
    is_valid_transition as validar_transicion,
)
from apps.claims.models import Reclamacion


def crear_reclamacion(solicitud, tipo, descripcion, evidencia=None, actor=None):
    """Create a new claim for a solicitud.

    Args:
        solicitud: The Solicitud object to claim
        tipo: Reclamacion.TipoReclamacion value
        descripcion: Text explaining the claim
        evidencia: Optional file attachment
        actor: User creating the claim

    Returns:
        Reclamacion instance
    """
    from apps.claims.models import Reclamacion, ReclamacionHistorial

    # Verify user owns the solicitud
    if actor and actor != solicitud.aspirante:
        raise PermissionError("Solo el aspirante puede presentar reclamaciones")

    # Create the claim
    reclamacion = Reclamacion.objects.create(
        solicitud=solicitud,
        tipo=tipo,
        descripcion=descripcion,
        evidencia=evidencia,
    )

    # Create initial history entry
    ReclamacionHistorial.objects.create(
        reclamacion=reclamacion,
        estado_anterior="",
        estado_nuevo=Reclamacion.Estado.PRESENTADA,
        observacion="Reclamación presentada",
        actor=actor,
    )

    return reclamacion


def cambiar_estado(reclamacion, nuevo_estado, observacion="", actor=None):
    """Change the state of a claim with validation.

    Args:
        reclamacion: Reclamacion instance
        nuevo_estado: Reclamacion.Estado value
        observacion: Optional observation
        actor: User performing the action

    Returns:
        Reclamacion instance
    """
    from apps.claims.models import ReclamacionHistorial

    estado_anterior = reclamacion.estado

    # Validate transition
    transicion_valida = validar_transicion(estado_anterior, nuevo_estado)
    if not transicion_valida:
        raise ValueError(f"Transición inválida: {estado_anterior} → {nuevo_estado}")

    # Update claim
    reclamacion.estado = nuevo_estado
    reclamacion.save()

    # Create history entry
    ReclamacionHistorial.objects.create(
        reclamacion=reclamacion,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        observacion=observacion,
        actor=actor,
    )

    return reclamacion


def iniciar_revision(reclamacion, actor):
    """Start the review process for a claim (Junta action)."""
    return cambiar_estado(
        reclamacion,
        Reclamacion.Estado.EN_REVISION,
        observacion="Junta inicia revisión de la reclamación",
        actor=actor,
    )


def resolver_reclamacion(reclamacion, respuesta, aceptar=True, actor=None):
    """Resolve a claim (Junta action).

    Args:
        reclamacion: Reclamacion instance
        respuesta: Text with the resolution explanation
        aceptar: If True, accept the claim; if False, reject it
        actor: User resolving (must be R-JUNTA)

    Returns:
        Reclamacion instance
    """
    from apps.claims.models import Reclamacion

    if actor and not actor.is_superuser:
        # Check if user has R-JUNTA role
        from apps.accounts.models import Role, UserRole

        junta_role = Role.objects.filter(code="R-JUNTA").first()
        if junta_role and not UserRole.objects.filter(user=actor, role=junta_role).exists():
            raise PermissionError("Solo R-JUNTA puede resolver reclamaciones")

    nuevo_estado = Reclamacion.Estado.RESUELTA if aceptar else Reclamacion.Estado.RECHAZADA

    observacion = "Reclamación aceptada" if aceptar else "Reclamación rechazada"

    # Update claim
    reclamacion.estado = nuevo_estado
    reclamacion.respuesta = respuesta
    reclamacion.resuelto_por = actor
    reclamacion.fecha_resolucion = timezone.now()
    reclamacion.save()

    # Create history entry
    from apps.claims.models import ReclamacionHistorial

    ReclamacionHistorial.objects.create(
        reclamacion=reclamacion,
        estado_anterior=Reclamacion.Estado.EN_REVISION,
        estado_nuevo=nuevo_estado,
        observacion=observacion,
        actor=actor,
    )

    return reclamacion
