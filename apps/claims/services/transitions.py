"""State transition services for apelaciones (CHG-206)."""
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone

from apps.claims.domain.transitions import (
    get_transition_label,
    is_valid_apelacion_transition,
)


def iniciar_analisis(apelacion, actor):
    """Start analysis of an appeal (OFIJUR action).

    Args:
        apelacion: Apelacion instance
        actor: User performing the action (must be R-OFIJUR)

    Returns:
        Apelacion instance

    Raises:
        ValidationError: If transition is invalid
        PermissionDenied: If actor is not R-OFIJUR
    """
    from apps.claims.models import Apelacion, ApelacionHistorial

    # 1. Validate actor has R-OFIJUR role
    if actor and not actor.is_superuser:
        from apps.accounts.models import Role, UserRole
        ofijur_role = Role.objects.filter(code="R-OFIJUR").first()
        if ofijur_role and not UserRole.objects.filter(user=actor, role=ofijur_role).exists():
            raise PermissionDenied("Solo R-OFIJUR puede iniciar análisis de apelaciones.")

    # 2. Validate transition
    nuevo_estado = Apelacion.Estado.EN_ANALISIS
    if not is_valid_apelacion_transition(apelacion.estado, nuevo_estado):
        raise ValidationError(
            f"Transición inválida para apelación en estado {apelacion.estado}."
        )

    # 3. Update appeal
    estado_anterior = apelacion.estado
    apelacion.estado = nuevo_estado
    apelacion.save()

    # 4. Create history entry
    ApelacionHistorial.objects.create(
        apelacion=apelacion,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        observacion="OFIJUR inicia análisis de la apelación",
        actor=actor,
    )

    return apelacion


def confirmar(apelacion, respuesta, actor):
    """Confirm an appeal (OFIJUR action).

    Args:
        apelacion: Apelacion instance
        respuesta: Text with the resolution explanation (must not be empty)
        actor: User performing the action (must be R-OFIJUR)

    Returns:
        Apelacion instance

    Raises:
        ValidationError: If transition is invalid or respuesta is empty
        PermissionDenied: If actor is not R-OFIJUR
    """
    from apps.claims.models import Apelacion, ApelacionHistorial

    # 1. Validate actor has R-OFIJUR role
    if actor and not actor.is_superuser:
        from apps.accounts.models import Role, UserRole
        ofijur_role = Role.objects.filter(code="R-OFIJUR").first()
        if ofijur_role and not UserRole.objects.filter(user=actor, role=ofijur_role).exists():
            raise PermissionDenied("Solo R-OFIJUR puede confirmar apelaciones.")

    # 2. Validate respuesta is not empty
    if not respuesta or not respuesta.strip():
        raise ValidationError("La respuesta no puede estar vacía.")

    # 3. Validate transition
    nuevo_estado = Apelacion.Estado.CONFIRMADA
    if not is_valid_apelacion_transition(apelacion.estado, nuevo_estado):
        raise ValidationError(
            f"Transición inválida para apelación en estado {apelacion.estado}."
        )

    # 4. Update appeal
    estado_anterior = apelacion.estado
    apelacion.estado = nuevo_estado
    apelacion.respuesta = respuesta.strip()
    apelacion.resuelto_por = actor
    apelacion.fecha_resolucion = timezone.now()
    apelacion.save()

    # 5. Create history entry
    ApelacionHistorial.objects.create(
        apelacion=apelacion,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        observacion="OFIJUR confirma la apelación",
        actor=actor,
    )

    return apelacion


def revocar(apelacion, respuesta, actor):
    """Revoke an appeal (OFIJUR action).

    Args:
        apelacion: Apelacion instance
        respuesta: Text with the resolution explanation (must not be empty)
        actor: User performing the action (must be R-OFIJUR)

    Returns:
        Apelacion instance

    Raises:
        ValidationError: If transition is invalid or respuesta is empty
        PermissionDenied: If actor is not R-OFIJUR
    """
    from apps.claims.models import Apelacion, ApelacionHistorial

    # 1. Validate actor has R-OFIJUR role
    if actor and not actor.is_superuser:
        from apps.accounts.models import Role, UserRole
        ofijur_role = Role.objects.filter(code="R-OFIJUR").first()
        if ofijur_role and not UserRole.objects.filter(user=actor, role=ofijur_role).exists():
            raise PermissionDenied("Solo R-OFIJUR puede revocar apelaciones.")

    # 2. Validate respuesta is not empty
    if not respuesta or not respuesta.strip():
        raise ValidationError("La respuesta no puede estar vacía.")

    # 3. Validate transition
    nuevo_estado = Apelacion.Estado.REVOCADA
    if not is_valid_apelacion_transition(apelacion.estado, nuevo_estado):
        raise ValidationError(
            f"Transición inválida para apelación en estado {apelacion.estado}."
        )

    # 4. Update appeal
    estado_anterior = apelacion.estado
    apelacion.estado = nuevo_estado
    apelacion.respuesta = respuesta.strip()
    apelacion.resuelto_por = actor
    apelacion.fecha_resolucion = timezone.now()
    apelacion.save()

    # 5. Create history entry
    ApelacionHistorial.objects.create(
        apelacion=apelacion,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        observacion="OFIJUR revoca la apelación",
        actor=actor,
    )

    return apelacion


def cambiar_estado_apelacion(apelacion, nuevo_estado, respuesta="", actor=None):
    """Generic state change for appeals with validation.

    Args:
        apelacion: Apelacion instance
        nuevo_estado: Apelacion.Estado value
        respuesta: Optional resolution text (required for confirmar/revocar)
        actor: User performing the action

    Returns:
        Apelacion instance

    Raises:
        ValidationError: If transition is invalid
        PermissionDenied: If actor lacks required role
    """
    from apps.claims.models import Apelacion, ApelacionHistorial

    estado_anterior = apelacion.estado

    # Validate transition
    if not is_valid_apelacion_transition(estado_anterior, nuevo_estado):
        raise ValidationError(
            f"Transición inválida: {estado_anterior} → {nuevo_estado}"
        )

    # Role validation based on transition
    if nuevo_estado in [Apelacion.Estado.EN_ANALISIS, Apelacion.Estado.CONFIRMADA, Apelacion.Estado.REVOCADA]:
        if actor and not actor.is_superuser:
            from apps.accounts.models import Role, UserRole
            ofijur_role = Role.objects.filter(code="R-OFIJUR").first()
            if ofijur_role and not UserRole.objects.filter(user=actor, role=ofijur_role).exists():
                raise PermissionDenied("Solo R-OFIJUR puede realizar esta transición.")

    # Validate respuesta for terminal states
    if nuevo_estado in [Apelacion.Estado.CONFIRMADA, Apelacion.Estado.REVOCADA]:
        if not respuesta or not respuesta.strip():
            raise ValidationError("La respuesta no puede estar vacía para estados terminales.")
        apelacion.respuesta = respuesta.strip()
        apelacion.resuelto_por = actor
        apelacion.fecha_resolucion = timezone.now()

    # Update appeal
    apelacion.estado = nuevo_estado
    apelacion.save()

    # Create history entry
    observacion = get_transition_label(estado_anterior, nuevo_estado)
    ApelacionHistorial.objects.create(
        apelacion=apelacion,
        estado_anterior=estado_anterior,
        estado_nuevo=nuevo_estado,
        observacion=observacion,
        actor=actor,
    )

    return apelacion
