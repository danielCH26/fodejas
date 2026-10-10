"""Services for apelaciones (CHG-206)."""

from django.utils import timezone


def validar_apelacion(reclamacion, actor):
    """Validate that an appeal can be created for a claim.

    Args:
        reclamacion: Reclamacion instance
        actor: User creating the appeal

    Returns:
        tuple: (is_valid, error_message)
    """
    from apps.claims.models import Apelacion, Reclamacion

    # Check claim is in terminal state
    if reclamacion.estado not in [
        Reclamacion.Estado.RESUELTA,
        Reclamacion.Estado.RECHAZADA,
    ]:
        return False, "Solo se puede apelar una reclamación resuelta o rechazada."

    # Check 30-day window
    if reclamacion.fecha_resolucion:
        days_since_resolution = (timezone.now() - reclamacion.fecha_resolucion).days
        if days_since_resolution > 30:
            return False, "El plazo de 30 días para apelar ha vencido."

    # Check user is the titular
    if actor != reclamacion.solicitud.aspirante:
        return False, "Solo el aspirante puede presentar apelaciones."

    # Check no existing pending apelacion
    existing = Apelacion.objects.filter(
        reclamacion=reclamacion,
        estado__in=[Apelacion.Estado.PRESENTADA, Apelacion.Estado.EN_ANALISIS],
    ).exists()
    if existing:
        return False, "Ya existe una apelación en curso para esta reclamación."

    return True, None


def crear_apelacion(reclamacion, descripcion, evidencia=None, actor=None):
    """Create a new appeal for a claim.

    Args:
        reclamacion: Reclamacion instance to appeal
        descripcion: Appeal grounds
        evidencia: Optional file attachment
        actor: User creating the appeal

    Returns:
        Apelacion instance
    """
    from apps.claims.models import Apelacion, ApelacionHistorial

    # Validate
    is_valid, error = validar_apelacion(reclamacion, actor)
    if not is_valid:
        raise ValueError(error)

    # Create the appeal
    apelacion = Apelacion.objects.create(
        reclamacion=reclamacion,
        descripcion=descripcion,
        evidencia=evidencia,
    )

    # Create initial history entry
    ApelacionHistorial.objects.create(
        apelacion=apelacion,
        estado_anterior="",
        estado_nuevo=Apelacion.Estado.PRESENTADA,
        observacion="Apelación presentada",
        actor=actor,
    )

    return apelacion


def iniciar_analisis(apelacion, actor):
    """Start analysis of an appeal (OFIJUR action).

    Args:
        apelacion: Apelacion instance
        actor: User starting analysis (must be R-OFIJUR)

    Returns:
        Apelacion instance
    """
    from apps.claims.models import Apelacion, ApelacionHistorial

    if apelacion.estado != Apelacion.Estado.PRESENTADA:
        raise ValueError("Solo se puede iniciar análisis de apelaciones presentadas.")

    # Verify actor is OFIJUR
    _verify_ofijur_role(actor)

    # Update state
    apelacion.estado = Apelacion.Estado.EN_ANALISIS
    apelacion.save()

    # Record history
    ApelacionHistorial.objects.create(
        apelacion=apelacion,
        estado_anterior=Apelacion.Estado.PRESENTADA,
        estado_nuevo=Apelacion.Estado.EN_ANALISIS,
        observacion="OFIJUR inicia análisis de la apelación",
        actor=actor,
    )

    return apelacion


def confirmar_apelacion(apelacion, respuesta, actor):
    """Confirm/accept an appeal (OFIJUR action).

    Args:
        apelacion: Apelacion instance
        respuesta: Resolution explanation
        actor: User confirming (must be R-OFIJUR)

    Returns:
        Apelacion instance
    """
    from apps.claims.models import Apelacion, ApelacionHistorial

    if apelacion.estado != Apelacion.Estado.EN_ANALISIS:
        raise ValueError("Solo se pueden confirmar apelaciones en análisis.")

    if not respuesta:
        raise ValueError("La respuesta es obligatoria.")

    # Verify actor is OFIJUR
    _verify_ofijur_role(actor)

    # Update appeal
    apelacion.estado = Apelacion.Estado.CONFIRMADA
    apelacion.respuesta = respuesta
    apelacion.resuelto_por = actor
    apelacion.fecha_resolucion = timezone.now()
    apelacion.save()

    # Record history
    ApelacionHistorial.objects.create(
        apelacion=apelacion,
        estado_anterior=Apelacion.Estado.EN_ANALISIS,
        estado_nuevo=Apelacion.Estado.CONFIRMADA,
        observacion="Apelación confirmada",
        actor=actor,
    )

    return apelacion


def revocar_apelacion(apelacion, respuesta, actor):
    """Reject an appeal (OFIJUR action).

    Args:
        apelacion: Apelacion instance
        respuesta: Rejection explanation
        actor: User rejecting (must be R-OFIJUR)

    Returns:
        Apelacion instance
    """
    from apps.claims.models import Apelacion, ApelacionHistorial

    if apelacion.estado != Apelacion.Estado.EN_ANALISIS:
        raise ValueError("Solo se pueden rechazar apelaciones en análisis.")

    if not respuesta:
        raise ValueError("La respuesta es obligatoria.")

    # Verify actor is OFIJUR
    _verify_ofijur_role(actor)

    # Update appeal
    apelacion.estado = Apelacion.Estado.REVOCADA
    apelacion.respuesta = respuesta
    apelacion.resuelto_por = actor
    apelacion.fecha_resolucion = timezone.now()
    apelacion.save()

    # Record history
    ApelacionHistorial.objects.create(
        apelacion=apelacion,
        estado_anterior=Apelacion.Estado.EN_ANALISIS,
        estado_nuevo=Apelacion.Estado.REVOCADA,
        observacion="Apelación rechazada",
        actor=actor,
    )

    return apelacion


def _verify_ofijur_role(user):
    """Verify user has R-OFIJUR role."""
    from apps.accounts.models import Role, UserRole

    if user.is_superuser:
        return True

    ofijur_role = Role.objects.filter(code="R-OFIJUR").first()
    if not ofijur_role:
        raise PermissionError("Rol R-OFIJUR no existe.")

    has_role = UserRole.objects.filter(user=user, role=ofijur_role).exists()
    if not has_role:
        raise PermissionError("Solo R-OFIJUR puede realizar esta acción.")

    return True
