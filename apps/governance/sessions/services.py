"""Session service for governance/sessions (CHG-501 / CAP-017).

All mutating operations are wrapped in ``@transaction.atomic`` and
emit CAP-022 audit events (module="governance", fail-closed).

Business rules (project.md §6.1.1-6.1.2, approved spec delta):
  - Quórum = mitad + 1 of members with voting rights; session cannot
    open without quórum.
  - Miembros por cargo (Gobernador, Alcalde, Secretario) attend but
    NEVER vote and do NOT count toward voting quórum.
  - Convocatoria: ORDINARIA ≥ 5 working days notice; EXTRAORDINARIA ≥ 2.
  - Voting: one vote per (member, punto); values A_FAVOR / EN_CONTRA /
    ABSTENCION; conflicto_declarado=True → vote rejected; member may
    change vote until punto is closed.
  - Punto resolution: simple majority of emitted votes
    (A_FAVOR > EN_CONTRA; ABSTENCION never counts) when closed.
  - Acta: generated when session FINALIZADA, PDF via WeasyPrint seam +
    SHA-256 stored, signed via ElectronicSigner (MockSigner by default)
    storing pre/post hashes + firmantes.
"""

from __future__ import annotations

import hashlib
from datetime import date, timedelta

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.audit.services import log_audit_event
from apps.governance.sessions.models import (
    ActaSesion,
    DeclaracionConflicto,
    MiembroSesion,
    OrdenDelDiaPunto,
    Sesion,
    Voto,
    VotoImpedimento,
)

# ---------------------------------------------------------------------------
# Working-day helpers (copied from treasury/tasks.py — no cross-import)
# ---------------------------------------------------------------------------


def _add_working_days(start: date, days: int) -> date:
    """Return ``start`` advanced by ``days`` working days (Mon–Fri).

    ``days`` may be negative (move backwards).
    """
    if days == 0:
        return start
    step = 1 if days > 0 else -1
    remaining = abs(days)
    cursor = start
    while remaining > 0:
        cursor = cursor + timedelta(days=step)
        if cursor.weekday() < 5:  # 0=Mon … 4=Fri
            remaining -= 1
    return cursor


def _working_days_between(start: date, end: date) -> int:
    """Return the number of working days strictly between ``start`` and ``end``."""
    if end == start:
        return 0
    step = 1 if end > start else -1
    cursor = start
    count = 0
    while cursor != end:
        cursor = cursor + timedelta(days=step)
        if cursor.weekday() < 5:  # 0=Mon, 4=Fri
            count += step
    return count


# ---------------------------------------------------------------------------
# SessionService
# ---------------------------------------------------------------------------


class SessionService:
    """Service for managing governance session lifecycle (CAP-017)."""

    # Minimum working-day notice before session (project.md §6.1.1)
    MIN_NOTICE_ORDINARIA = 5
    MIN_NOTICE_EXTRAORDINARIA = 2

    # -------------------------------------------------------------------------
    # Convocation
    # -------------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def convocar_sesion(
        organo: str,
        tipo: str,
        fecha_hora,
        asunto: str,
        convocatoria_id=None,
        actor=None,
    ) -> Sesion:
        """Create a session in CONVOCADA state.

        Validates working-day notice:
          - ORDINARIA → ≥ 5 working days between now and fecha_hora.
          - EXTRAORDINARIA → ≥ 2 working days.

        Args:
            organo: JUNTA or CT
            tipo: ORDINARIA or EXTRAORDINARIA
            fecha_hora: datetime of the session
            asunto: session subject
            convocatoria_id: optional FK to Convocatory
            actor: CustomUser triggering the convocation (for audit)

        Returns:
            Sesion instance in CONVOCADA state

        Raises:
            ValueError: if notice period is insufficient or organo/tipo invalid
        """
        # Validate organo
        if organo not in (Sesion.Organo.JUNTA, Sesion.Organo.CT):
            raise ValueError(f"Órgano inválido: {organo}")

        # Validate tipo
        if tipo not in (Sesion.Tipo.ORDINARIA, Sesion.Tipo.EXTRAORDINARIA):
            raise ValueError(f"Tipo de sesión inválido: {tipo}")

        # Validate working-day notice
        if isinstance(fecha_hora, str):
            # Accept ISO datetime/date strings (API payloads arrive as
            # JSON strings).
            from datetime import datetime as _dt

            fecha_hora = _dt.fromisoformat(fecha_hora)
        today = timezone.now().date()
        session_date = fecha_hora.date() if hasattr(fecha_hora, "date") else fecha_hora

        min_notice = (
            SessionService.MIN_NOTICE_ORDINARIA
            if tipo == Sesion.Tipo.ORDINARIA
            else SessionService.MIN_NOTICE_EXTRAORDINARIA
        )

        notice_days = _working_days_between(today, session_date)
        if notice_days < min_notice:
            tipo_label = "ordinaria" if tipo == Sesion.Tipo.ORDINARIA else "extraordinaria"
            raise ValueError(
                f"Convocatoria {tipo_label} requiere al menos "
                f"{min_notice} días hábiles de anticipación; "
                f"solo hay {notice_days} días hábiles entre hoy y la fecha "
                f"de la sesión."
            )

        sesion = Sesion.objects.create(
            organo=organo,
            tipo=tipo,
            fecha_hora=fecha_hora,
            asunto=asunto,
            convocatoria_id=convocatoria_id,
            estado=Sesion.Estado.CONVOCADA,
            convocatoria_enviada_at=timezone.now(),
        )

        log_audit_event(
            actor=actor,
            action="SESSION_CONVOCAR",
            entity="Sesion",
            entity_id=sesion.id,
            changes={
                "organo": organo,
                "tipo": tipo,
                "fecha_hora": sesion.fecha_hora.isoformat(),
                "asunto": asunto,
                "convocatoria_id": str(convocatoria_id) if convocatoria_id else None,
                "working_days_notice": notice_days,
                "min_notice_required": min_notice,
            },
            module="governance",
        )

        return sesion

    # -------------------------------------------------------------------------
    # Attendance
    # -------------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def registrar_asistencia(
        sesion_id,
        member_records: list[dict],
        actor=None,
    ) -> list[MiembroSesion]:
        """Register or update attendance for session members.

        ``member_records`` is a list of dicts with keys:
          user_id, rol, asistencia (PRESENTE|VIRTUAL|AUSENTE),
          es_miembro_cargo, conflicto_declarado.

        Only valid when sesion is in CONVOCADA state.

        Args:
            sesion_id: Sesion UUID
            member_records: list of member attendance records
            actor: CustomUser triggering the registration (for audit)

        Returns:
            List of created/updated MiembroSesion instances

        Raises:
            ValueError: if session not in CONVOCADA state
        """
        sesion = Sesion.objects.select_for_update().get(id=sesion_id)

        if sesion.estado != Sesion.Estado.CONVOCADA:
            raise ValueError(
                f"No se puede registrar asistencia en estado {sesion.estado}; "
                "la sesión debe estar en estado CONVOCADA."
            )

        from django.contrib.auth import get_user_model

        CustomUser = get_user_model()
        results = []

        for record in member_records:
            user = CustomUser.objects.get(id=record["user_id"])
            miembro, _ = MiembroSesion.objects.update_or_create(
                sesion=sesion,
                user=user,
                defaults={
                    "rol": record.get("rol", ""),
                    "asistencia": record.get("asistencia", MiembroSesion.Asistencia.AUSENTE),
                    "es_miembro_cargo": record.get("es_miembro_cargo", False),
                    "conflicto_declarado": record.get("conflicto_declarado", False),
                },
            )
            results.append(miembro)

        log_audit_event(
            actor=actor,
            action="SESSION_ASISTENCIA",
            entity="Sesion",
            entity_id=sesion.id,
            changes={
                "member_count": len(results),
                "members": [
                    {"user_id": str(r.user_id), "asistencia": r.asistencia} for r in results
                ],
            },
            module="governance",
        )

        return results

    # -------------------------------------------------------------------------
    # Open session
    # -------------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def abrir_sesion(sesion_id, actor=None) -> Sesion:
        """Transition session from CONVOCADA → EN_SESION.

        Requires quorum (mitad + 1 of present voting members;
        cargo-exempt members do NOT count).

        Args:
            sesion_id: Sesion UUID
            actor: CustomUser opening the session (for audit)

        Returns:
            Updated Sesion in EN_SESION state

        Raises:
            ValueError: if session not in CONVOCADA or quórum not met
        """
        sesion = Sesion.objects.select_for_update().get(id=sesion_id)

        if sesion.estado != Sesion.Estado.CONVOCADA:
            raise ValueError(f"La sesión no está en estado CONVOCADA ({sesion.estado}).")

        if not sesion.quorum_met():
            voting_present = sesion.voting_members_present()
            raise ValueError(
                f"No hay quórum. Se requieren mayoría simple (mitad+1) de "
                f"miembros con derecho a voto. Miembros con voto presentes: "
                f"{voting_present}."
            )

        previous_estado = sesion.estado
        sesion.estado = Sesion.Estado.EN_SESION
        sesion.save(update_fields=["estado", "updated_at"])

        log_audit_event(
            actor=actor,
            action="SESSION_ABRIR",
            entity="Sesion",
            entity_id=sesion.id,
            changes={
                "previous_estado": previous_estado,
                "estado": sesion.estado,
                "voting_members_present": sesion.voting_members_present(),
            },
            module="governance",
        )

        return sesion

    # -------------------------------------------------------------------------
    # Agenda
    # -------------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def agregar_punto(
        sesion_id,
        numero: int,
        texto: str,
        actor=None,
    ) -> OrdenDelDiaPunto:
        """Add an agenda punto to a session (only while CONVOCADA).

        Args:
            sesion_id: Sesion UUID
            numero: agenda order number (unique per session)
            texto: punto text
            actor: CustomUser adding the punto (for audit)

        Returns:
            Created OrdenDelDiaPunto

        Raises:
            ValueError: if session not in CONVOCADA or numero already used
        """
        sesion = Sesion.objects.select_for_update().get(id=sesion_id)

        if sesion.estado != Sesion.Estado.CONVOCADA:
            raise ValueError(
                f"Solo se pueden agregar puntos mientras la sesión está "
                f"en estado CONVOCADA (estado actual: {sesion.estado})."
            )

        if sesion.puntos.filter(numero=numero).exists():
            raise ValueError(f"Ya existe un punto con número {numero} en esta sesión.")

        punto = OrdenDelDiaPunto.objects.create(
            sesion=sesion,
            numero=numero,
            texto=texto,
            estado=OrdenDelDiaPunto.Estado.PENDIENTE,
        )

        log_audit_event(
            actor=actor,
            action="SESSION_PUNTO_AGREGAR",
            entity="OrdenDelDiaPunto",
            entity_id=str(punto.id),
            changes={
                "sesion_id": str(sesion_id),
                "numero": numero,
                "texto": texto[:100],
            },
            module="governance",
        )

        return punto

    # -------------------------------------------------------------------------
    # Voting
    # -------------------------------------------------------------------------

    @staticmethod
    def _voting_blockers(miembro, punto) -> list[str]:
        """Reasons why ``miembro`` cannot vote on ``punto`` (CHG-501/502)."""
        reasons = []
        if not miembro.can_vote():
            reasons.append("el miembro no puede votar")
        if miembro.asistencia == MiembroSesion.Asistencia.AUSENTE:
            reasons.append("ausente")
        if miembro.es_miembro_cargo:
            reasons.append("miembro por cargo (no vota)")
        if miembro.conflicto_declarado:
            reasons.append("conflicto de interés declarado")
        # CHG-502: formal COI declarations on THIS punto also block.
        if DeclaracionConflicto.objects.filter(
            miembro_sesion=miembro,
            punto=punto,
            estado__in=[
                DeclaracionConflicto.Estado.PENDIENTE,
                DeclaracionConflicto.Estado.APROBADA,
            ],
        ).exists():
            reasons.append(
                "impedimento de conflicto de interés en trámite o aprobado para este punto"
            )
        return reasons

    @staticmethod
    @transaction.atomic
    def registrar_voto(
        sesion_id,
        punto_id,
        miembro_sesion_id: int,
        valor: str,
        actor=None,
    ) -> Voto:
        """Cast or update a vote on an open agenda punto.

        Rules:
          - Session must be EN_SESION.
          - Punto must be PENDIENTE.
          - Member must be present/virtual (not AUSENTE).
          - Member must NOT be cargo-exempt.
          - Member must NOT have conflicto_declarado=True.
          - Vote may be updated until punto is closed.

        Args:
            sesion_id: Sesion UUID
            punto_id: OrdenDelDiaPunto UUID
            miembro_sesion_id: MiembroSesion primary key
            valor: A_FAVOR, EN_CONTRA, or ABSTENCION
            actor: CustomUser casting the vote (for audit)

        Returns:
            Created or updated Voto

        Raises:
            ValueError: if session/punto in wrong state or member cannot vote
        """
        sesion = Sesion.objects.select_for_update().get(id=sesion_id)

        if sesion.estado != Sesion.Estado.EN_SESION:
            raise ValueError(f"La sesión no está en estado EN_SESION ({sesion.estado}).")

        try:
            punto = OrdenDelDiaPunto.objects.select_for_update().get(id=punto_id, sesion=sesion)
        except OrdenDelDiaPunto.DoesNotExist:
            raise ValueError(
                f"Punto {punto_id} no encontrado o no pertenece a la sesión."
            ) from None

        if punto.estado != OrdenDelDiaPunto.Estado.PENDIENTE:
            raise ValueError(f"El punto {punto.numero} ya está cerrado (estado: {punto.estado}).")

        try:
            miembro = MiembroSesion.objects.get(id=miembro_sesion_id, sesion=sesion)
        except MiembroSesion.DoesNotExist:
            raise ValueError(
                f"MiembroSesion {miembro_sesion_id} no encontrado en la sesión."
            ) from None

        blockers = SessionService._voting_blockers(miembro, punto)
        if blockers:
            raise ValueError(f"El miembro {miembro.user} no puede votar: {', '.join(blockers)}.")

        if valor not in (Voto.Valor.A_FAVOR, Voto.Valor.EN_CONTRA, Voto.Valor.ABSTENCION):
            raise ValueError(f"Valor de voto inválido: {valor}")

        voto, created = Voto.objects.update_or_create(
            punto=punto,
            miembro_sesion=miembro,
            defaults={"valor": valor},
        )

        log_audit_event(
            actor=actor,
            action="SESSION_VOTO",
            entity="Voto",
            entity_id=str(voto.id),
            changes={
                "sesion_id": str(sesion_id),
                "punto_numero": punto.numero,
                "miembro_user_id": str(miembro.user_id),
                "valor": valor,
                "created": created,
            },
            module="governance",
        )

        return voto

    @staticmethod
    @transaction.atomic
    def cerrar_punto(punto_id, actor=None) -> OrdenDelDiaPunto:
        """Close an open agenda punto and compute the result.

        Resolution: simple majority of emitted votes.
          - A_FAVOR > EN_CONTRA → APROBADO
          - EN_CONTRA >= A_FAVOR → RECHAZADO (includes tie)
          - ABSTENCION never counts toward majority.

        Args:
            punto_id: OrdenDelDiaPunto UUID
            actor: CustomUser closing the punto (for audit)

        Returns:
            Updated OrdenDelDiaPunto with APROBADO or RECHAZADO
        """
        punto = OrdenDelDiaPunto.objects.select_for_update().get(id=punto_id)

        if punto.estado != OrdenDelDiaPunto.Estado.PENDIENTE:
            raise ValueError(f"El punto {punto.numero} ya está cerrado (estado: {punto.estado}).")

        sesion = punto.sesion

        a_favor = punto.votos.filter(valor=Voto.Valor.A_FAVOR).count()
        en_contra = punto.votos.filter(valor=Voto.Valor.EN_CONTRA).count()

        # Simple majority: A_FAVOR strictly greater than EN_CONTRA
        resultado = (
            OrdenDelDiaPunto.Estado.APROBADO
            if a_favor > en_contra
            else OrdenDelDiaPunto.Estado.RECHAZADO
        )

        previous_estado = punto.estado
        punto.estado = resultado
        punto.save(update_fields=["estado"])

        log_audit_event(
            actor=actor,
            action="SESSION_PUNTO_CERRAR",
            entity="OrdenDelDiaPunto",
            entity_id=str(punto.id),
            changes={
                "sesion_id": str(sesion.id),
                "punto_numero": punto.numero,
                "previous_estado": previous_estado,
                "resultado": resultado,
                "votos_a_favor": a_favor,
                "votos_en_contra": en_contra,
                "abstenciones": punto.votos.filter(valor=Voto.Valor.ABSTENCION).count(),
            },
            module="governance",
        )

        return punto

    # -------------------------------------------------------------------------
    # Finalize
    # -------------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def finalizar_sesion(sesion_id, actor=None) -> Sesion:
        """Transition session from EN_SESION → FINALIZADA.

        All puntos must be closed before finalization.

        Args:
            sesion_id: Sesion UUID
            actor: CustomUser finalizing (for audit)

        Returns:
            Updated Sesion in FINALIZADA state
        """
        sesion = Sesion.objects.select_for_update().get(id=sesion_id)

        if sesion.estado != Sesion.Estado.EN_SESION:
            raise ValueError(f"La sesión no está en estado EN_SESION ({sesion.estado}).")

        if not sesion.all_puntos_closed():
            open_puntos = sesion.puntos.filter(
                estado=OrdenDelDiaPunto.Estado.PENDIENTE
            ).values_list("numero", flat=True)
            raise ValueError(
                f"No se puede finalizar: hay puntos pendientes: " f"{list(open_puntos)}."
            )

        previous_estado = sesion.estado
        sesion.estado = Sesion.Estado.FINALIZADA
        sesion.save(update_fields=["estado", "updated_at"])

        log_audit_event(
            actor=actor,
            action="SESSION_FINALIZAR",
            entity="Sesion",
            entity_id=sesion.id,
            changes={
                "previous_estado": previous_estado,
                "estado": sesion.estado,
            },
            module="governance",
        )

        return sesion

    # -------------------------------------------------------------------------
    # Acta (minutes)
    # -------------------------------------------------------------------------

    @staticmethod
    def generar_acta(sesion_id, actor=None) -> ActaSesion:
        """Generate the session minutes PDF and compute SHA-256.

        The PDF is generated via the governance PDF seam (lazy import of
        WeasyPrint). The SHA-256 hash is stored on the ActaSesion.

        This method is idempotent — calling it again replaces the PDF
        and recomputes the hash.

        Args:
            sesion_id: Sesion UUID
            actor: CustomUser generating the acta (for audit)

        Returns:
            ActaSesion with pdf and pdf_sha256 set
        """
        sesion = Sesion.objects.select_for_update().get(id=sesion_id)

        if sesion.estado != Sesion.Estado.FINALIZADA:
            raise ValueError(
                f"El acta solo puede generarse para sesiones FINALIZADAS "
                f"(estado actual: {sesion.estado})."
            )

        # Generate PDF bytes using the governance PDF seam
        try:
            pdf_bytes = SessionService._generar_pdf_bytes(sesion)
        except Exception as exc:
            raise RuntimeError(f"Error generando PDF del acta: {exc}") from exc

        sha256_hash = hashlib.sha256(pdf_bytes).hexdigest()

        acta, _ = ActaSesion.objects.update_or_create(
            sesion=sesion,
            defaults={
                "pdf_sha256": sha256_hash,
                "estado": ActaSesion.Estado.GENERADA,
            },
        )
        # Save the PDF file
        filename = f"acta_{sesion.id}.pdf"
        acta.pdf.save(filename, ContentFile(pdf_bytes), save=True)

        log_audit_event(
            actor=actor,
            action="SESSION_ACTA_GENERAR",
            entity="ActaSesion",
            entity_id=acta.sesion_id,
            changes={
                "sesion_id": str(sesion_id),
                "sha256": sha256_hash,
                "pdf_name": filename,
            },
            module="governance",
        )

        return acta

    @staticmethod
    def _generar_pdf_bytes(sesion: Sesion) -> bytes:
        """Generate PDF bytes for a session's acta (WeasyPrint lazy import).

        Uses ``apps.governance.services.pdf.generar_pdf_acto`` as the seam
        with a fallback that builds a minimal HTML document directly.

        Args:
            sesion: Sesion instance

        Returns:
            Raw PDF bytes
        """
        # Try the governance PDF seam first
        try:
            from apps.governance.services.pdf import generar_pdf_acto
        except ImportError:
            generar_pdf_acto = None

        if generar_pdf_acto is not None:
            try:
                return generar_pdf_acto(sesion)
            except Exception:
                pass

        # Fallback: build a minimal HTML document directly with WeasyPrint
        try:
            from weasyprint import HTML  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "WeasyPrint no está instalado. Instala con: pip install weasyprint"
            ) from exc

        # Build puntos HTML
        puntos_html = ""
        for punto in sesion.puntos.all():
            estado_punto = punto.get_estado_display()
            puntos_html += f"""
            <tr>
                <td>{punto.numero}</td>
                <td>{punto.texto}</td>
                <td>{estado_punto}</td>
            </tr>
            """

        miembros_html = "".join(
            f"<li>{m.user.get_full_name() or m.user.email} ({m.get_asistencia_display()}){' — MIEMBRO POR CARGO' if m.es_miembro_cargo else ''}{' — CONFLICTO DE INTERÉS' if m.conflicto_declarado else ''}</li>"
            for m in sesion.miembros.select_related("user").all()
        )

        html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<title>Acta de Sesión {sesion.get_tipo_display()} {sesion.get_organo_display()}</title>
<style>
body {{ font-family: sans-serif; margin: 2cm; }}
h1 {{ text-align: center; }}
table {{ width: 100%; border-collapse: collapse; margin-top: 1em; }}
th, td {{ border: 1px solid #333; padding: 0.4em; text-align: left; }}
th {{ background: #f0f0f0; }}
</style>
</head>
<body>
<h1>Acta de Sesión</h1>
<p><strong>Tipo:</strong> {sesion.get_tipo_display()}</p>
<p><strong>Órgano:</strong> {sesion.get_organo_display()}</p>
<p><strong>Fecha y hora:</strong> {sesion.fecha_hora.strftime('%d/%m/%Y %H:%M')}</p>
<p><strong>Asunto:</strong> {sesion.asunto}</p>

<h2>Miembros asistentes</h2>
<ul>{miembros_html}</ul>

<h2>Orden del Día</h2>
<table>
<tr><th>#</th><th>Punto</th><th>Resultado</th></tr>
{puntos_html}
</table>
</body>
</html>"""

        return HTML(string=html_content).write_pdf()

    # -------------------------------------------------------------------------
    # Sign
    # -------------------------------------------------------------------------

    @staticmethod
    @transaction.atomic
    def firmar_acta(
        sesion_id,
        firmantes: list[str],
        actor=None,
    ) -> ActaSesion:
        """Sign the session minutes with the ElectronicSigner abstraction.

        Uses ``SignerFactory.get_provider()`` (MockSigner by default).
        Stores pre_sign_hash, post_sign_hash, firmantes list, and
        signed_at on the ActaSesion.

        Args:
            sesion_id: Sesion UUID
            firmantes: list of signer names
            actor: CustomUser signing (for audit)

        Returns:
            Updated ActaSesion in FIRMADA state
        """
        sesion = Sesion.objects.select_for_update().get(id=sesion_id)

        try:
            acta = ActaSesion.objects.select_for_update().get(sesion=sesion)
        except ActaSesion.DoesNotExist:
            raise ValueError(
                f"No existe acta para la sesión {sesion_id}. "
                "Genere el acta primero con generar_acta()."
            ) from None

        if not acta.pdf:
            raise ValueError("El acta no tiene archivo PDF adjunto.")

        # Read PDF bytes
        with acta.pdf.open("rb") as f:
            pdf_bytes = f.read()

        # Sign using the ElectronicSigner abstraction
        from apps.legalization.signer import SignerFactory

        signer = SignerFactory.get_provider()
        result = signer.sign(pdf_bytes)

        # Store signature data
        acta.pre_sign_hash = result.pre_sign_hash
        acta.post_sign_hash = result.post_sign_hash
        acta.firmantes = [{"nombre": f, "hash": result.post_sign_hash} for f in firmantes]
        acta.estado = ActaSesion.Estado.FIRMADA
        acta.signed_at = timezone.now()
        acta.save(
            update_fields=[
                "pre_sign_hash",
                "post_sign_hash",
                "firmantes",
                "estado",
                "signed_at",
            ]
        )

        log_audit_event(
            actor=actor,
            action="SESSION_ACTA_FIRMA",
            entity="ActaSesion",
            entity_id=acta.sesion_id,
            changes={
                "sesion_id": str(sesion_id),
                "pre_sign_hash": result.pre_sign_hash,
                "post_sign_hash": result.post_sign_hash,
                "firmantes": firmantes,
                "provider": result.provider,
            },
            module="governance",
        )

        return acta

    # ------------------------------------------------------------------
    # CHG-502 — Conflictos de interés (CAP-018, Ley 1952/2019)
    # ------------------------------------------------------------------

    @staticmethod
    def declarar_conflicto(
        sesion_id, punto_id, miembro_sesion_id: int, texto: str, actor=None
    ) -> DeclaracionConflicto:
        """Declare a conflict of interest on a punto (self-declaration).

        Rules:
          - Only the member themselves declares (ownership enforced by
            the caller passing their own miembro_sesion_id; the API
            resolves it from request.user).
          - The punto must be open (PENDIENTE) and the session in
            EN_SESION.
          - The declaration starts PENDIENTE, which blocks the
            member's vote on that punto until the impediment resolves.
        """
        punto = OrdenDelDiaPunto.objects.select_for_update().get(id=punto_id)
        if str(punto.sesion_id) != str(sesion_id):
            raise ValueError("El punto no pertenece a esta sesión.")
        if punto.estado != OrdenDelDiaPunto.Estado.PENDIENTE:
            raise ValueError("El punto ya está cerrado; no se pueden declarar conflictos.")
        miembro = MiembroSesion.objects.get(id=miembro_sesion_id, sesion_id=sesion_id)
        if not texto or not texto.strip():
            raise ValueError("La declaración requiere texto.")

        declaracion = DeclaracionConflicto.objects.create(
            miembro_sesion=miembro,
            punto=punto,
            texto=texto,
            estado=DeclaracionConflicto.Estado.PENDIENTE,
        )
        log_audit_event(
            actor=actor,
            action="SESSION_CONFLICTO_DECLARAR",
            entity="DeclaracionConflicto",
            entity_id=str(declaracion.id),
            changes={
                "punto_id": str(punto.id),
                "miembro": str(miembro.user),
                "estado": declaracion.estado,
            },
            module="governance",
        )
        return declaracion

    @staticmethod
    def votar_impedimento(
        declaracion_id, miembro_sesion_id: int, a_favor: bool, actor=None
    ) -> DeclaracionConflicto:
        """Cast an impediment vote and resolve by simple majority.

        Voters: the OTHER present voting members (the declarant cannot
        vote their own impediment). Resolution threshold: mitad + 1 of
        the present voting members excluding the declarant.
        """
        declaracion = DeclaracionConflicto.objects.select_for_update().get(id=declaracion_id)
        if declaracion.estado != DeclaracionConflicto.Estado.PENDIENTE:
            raise ValueError(f"El impedimento ya fue resuelto ({declaracion.estado}).")

        punto = declaracion.punto
        sesion = punto.sesion
        votante = MiembroSesion.objects.get(id=miembro_sesion_id, sesion=sesion)

        if votante.id == declaracion.miembro_sesion_id:
            raise ValueError("El declarante no puede votar su propio impedimento.")
        if votante.es_miembro_cargo:
            raise ValueError("Los miembros por cargo no votan impedimentos.")
        if votante.asistencia == MiembroSesion.Asistencia.AUSENTE:
            raise ValueError("Solo los miembros presentes votan impedimentos.")
        if votante.conflicto_declarado:
            raise ValueError("El votante tiene conflicto de interés declarado.")

        VotoImpedimento.objects.update_or_create(
            declaracion=declaracion,
            miembro_sesion=votante,
            defaults={"a_favor": a_favor},
        )

        # Present voting members excluding the declarant
        habilitados = (
            sesion.miembros.filter(
                es_miembro_cargo=False,
                conflicto_declarado=False,
            )
            .exclude(asistencia=MiembroSesion.Asistencia.AUSENTE)
            .exclude(id=declaracion.miembro_sesion_id)
            .count()
        )
        mayoria = habilitados // 2 + 1

        a_favor_count = declaracion.votos_impedimento.filter(a_favor=True).count()
        en_contra_count = declaracion.votos_impedimento.filter(a_favor=False).count()

        if a_favor_count >= mayoria:
            declaracion.estado = DeclaracionConflicto.Estado.APROBADA
        elif en_contra_count >= mayoria:
            declaracion.estado = DeclaracionConflicto.Estado.RECHAZADA
        else:
            declaracion.save(update_fields=[])
            log_audit_event(
                actor=actor,
                action="SESSION_IMPEDIMENTO_VOTO",
                entity="DeclaracionConflicto",
                entity_id=str(declaracion.id),
                changes={"a_favor": a_favor, "resuelto": False},
                module="governance",
            )
            return declaracion

        declaracion.revisado_at = timezone.now()
        declaracion.save(update_fields=["estado", "revisado_at"])
        log_audit_event(
            actor=actor,
            action="SESSION_IMPEDIMENTO_RESUELTO",
            entity="DeclaracionConflicto",
            entity_id=str(declaracion.id),
            changes={
                "estado": declaracion.estado,
                "a_favor": a_favor_count,
                "en_contra": en_contra_count,
                "habilitados": habilitados,
            },
            module="governance",
        )
        return declaracion
