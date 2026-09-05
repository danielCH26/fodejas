"""HTML views for applications."""
import hashlib

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.accounts.permissions_mixin import PermissionMixin, ReviewerPermissionMixin
from apps.applications.models import Anexo, RequisitoValidacion, Solicitud
from apps.applications.services.wizard_service import WizardError, save_draft, submit
from apps.convocatories.models import Convocatory


class ApplicationApplyView(LoginRequiredMixin, PermissionMixin, View):
    """Create application and redirect to wizard."""

    def get(self, request, pk):
        """Create a new application for the given convocation."""
        # Get convocation
        convocatoria = get_object_or_404(Convocatory, pk=pk)

        # Check if user already has an application for this convocation
        existing = Solicitud.objects.filter(
            convocatoria=convocatoria,
            aspirante=request.user
        ).first()

        if existing:
            # Redirect to existing application
            return redirect("applications:wizard_step", pk=str(existing.uuid), step=1)

        # Check convocation is in inscription state
        if convocatoria.estado != Convocatory.Estado.EN_INSCRIPCION:
            messages.error(request, "Las inscripciones para esta convocatoria están cerradas.")
            return redirect("convocatories:detail", pk=pk)

        # Create new application
        solicitud = Solicitud.objects.create(
            convocatoria=convocatoria,
            aspirante=request.user,
            estado=Solicitud.Estado.BORRADOR,
            current_step=1,
        )

        messages.success(request, "Tu solicitud ha sido iniciada. Completa los datos requeridos.")
        return redirect("applications:wizard_step", pk=str(solicitud.uuid), step=1)


class ApplicationListView(LoginRequiredMixin, PermissionMixin, ListView):
    """List view for user's applications."""

    model = Solicitud
    template_name = "applications/list.html"
    context_object_name = "applications"

    def get_queryset(self):
        """Return only the authenticated user's applications."""
        return Solicitud.objects.filter(
            aspirante=self.request.user
        ).select_related(
            "convocatoria"
        ).order_by("-created_at")


class ApplicationDetailView(LoginRequiredMixin, PermissionMixin, DetailView):
    """Detail view for a specific application."""

    model = Solicitud
    template_name = "applications/detail.html"
    context_object_name = "application"

    def get_object(self, queryset=None):
        """Get application by UUID and ensure user ownership."""
        uuid = self.kwargs.get("pk")
        return get_object_or_404(
            Solicitud.objects.filter(aspirante=self.request.user).select_related(
                "convocatoria"
            ).prefetch_related("anexos"),
            uuid=uuid
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        solicitud = context["application"]

        # Get scoring info if available
        try:
            if hasattr(solicitud, 'puntaje_total'):
                context["puntaje_total"] = solicitud.puntaje_total
        except:
            pass

        # Check if user can present a claim (results published)
        from apps.scoring.models import PuntajeTotal
        has_score = PuntajeTotal.objects.filter(solicitud=solicitud).exists()
        context["resultados_publicados"] = has_score

        return context


class ApplicationWizardView(LoginRequiredMixin, PermissionMixin, TemplateView):
    """Wizard view for FUI application."""

    template_name = "applications/wizard.html"

    def get_context_data(self, **kwargs):
        """Add application and current step to context."""
        context = super().get_context_data(**kwargs)

        # Get application by UUID
        uuid = self.kwargs.get("pk")
        application = get_object_or_404(
            Solicitud.objects.filter(aspirante=self.request.user),
            uuid=uuid
        )

        context["application"] = application
        context["current_step"] = application.current_step

        # Wizard step definitions
        context["steps"] = [
            {
                "number": 1,
                "title": "Datos Personales",
                "description": "Información personal básica",
                "partial_template": "applications/partials/wizard_step_1.html",
            },
            {
                "number": 2,
                "title": "Información Académica",
                "description": "Historial educativo y excelencia",
                "partial_template": "applications/partials/wizard_step_2.html",
            },
            {
                "number": 3,
                "title": "Información Socioeconómica",
                "description": "Contexto familiar y económico",
                "partial_template": "applications/partials/wizard_step_3.html",
            },
            {
                "number": 4,
                "title": "Anexos",
                "description": "Documentos de soporte",
                "partial_template": "applications/partials/wizard_step_4.html",
            },
            {
                "number": 5,
                "title": "Declaración y Consentimiento",
                "description": "Aceptación de términos",
                "partial_template": "applications/partials/wizard_step_5.html",
            },
        ]

        return context

    def post(self, request, *args, **kwargs):
        """Handle wizard step save via HTMX or form POST."""
        uuid = self.kwargs.get("pk")
        application = get_object_or_404(
            Solicitud.objects.filter(aspirante=self.request.user),
            uuid=uuid
        )

        step = int(request.POST.get("step", application.current_step))

        # Collect step data based on step number
        if step == 1:
            data = {
                "nombre": request.POST.get("nombre", ""),
                "apellido": request.POST.get("apellido", ""),
                "tipo_documento": request.POST.get("tipo_documento", ""),
                "numero_documento": request.POST.get("numero_documento", ""),
                "fecha_nacimiento": request.POST.get("fecha_nacimiento", ""),
                "genero": request.POST.get("genero", ""),
            }
        elif step == 2:
            data = {
                "programa": request.POST.get("programa", ""),
                "semestre": request.POST.get("semestre", ""),
                "promedio": request.POST.get("promedio", ""),
                "ies": request.POST.get("ies", ""),
            }
        elif step == 3:
            data = {
                "estrato": request.POST.get("estrato", ""),
                "ingresos": request.POST.get("ingresos", ""),
                "personas_cargo": request.POST.get("personas_cargo", ""),
            }
        elif step == 5:
            # Step 5 is declaration/consent - handle submit
            consentimiento = request.POST.get("consentimiento") == "on"
            try:
                submit(application, consentimiento, request.user)
                messages.success(request, f"Solicitud radicada: {application.radicado}")
                return JsonResponse({"success": True, "redirect": reverse_lazy("applications:detail", args=[application.uuid])})
            except WizardError as e:
                messages.error(request, str(e))
                return JsonResponse({"success": False, "error": str(e)}, status=400)
        else:
            data = {}

        # Save draft for steps 1-3
        if step in [1, 2, 3]:
            try:
                save_draft(application, step, data)
                application.current_step = step + 1
                application.save(update_fields=["current_step", "updated_at"])
                messages.success(request, "Datos guardados correctamente")
                return JsonResponse({"success": True, "next_step": step + 1})
            except WizardError as e:
                messages.error(request, str(e))
                return JsonResponse({"success": False, "error": str(e)}, status=400)

        return JsonResponse({"success": True})


class ApplicationWizardStepView(LoginRequiredMixin, PermissionMixin, TemplateView):
    """View for specific wizard step."""

    template_name = "applications/wizard.html"

    def get_context_data(self, **kwargs):
        """Add application and specific step to context."""
        context = super().get_context_data(**kwargs)

        # Get application by UUID
        uuid = self.kwargs.get("pk")
        application = get_object_or_404(
            Solicitud.objects.filter(aspirante=self.request.user),
            uuid=uuid
        )

        step = int(self.kwargs.get("step", application.current_step))

        context["application"] = application
        context["current_step"] = step

        # Wizard step definitions (same as parent view)
        context["steps"] = [
            {
                "number": 1,
                "title": "Datos Personales",
                "description": "Información personal básica",
                "partial_template": "applications/partials/wizard_step_1.html",
            },
            {
                "number": 2,
                "title": "Información Académica",
                "description": "Historial educativo y excelencia",
                "partial_template": "applications/partials/wizard_step_2.html",
            },
            {
                "number": 3,
                "title": "Información Socioeconómica",
                "description": "Contexto familiar y económico",
                "partial_template": "applications/partials/wizard_step_3.html",
            },
            {
                "number": 4,
                "title": "Anexos",
                "description": "Documentos de soporte",
                "partial_template": "applications/partials/wizard_step_4.html",
            },
            {
                "number": 5,
                "title": "Declaración y Consentimiento",
                "description": "Aceptación de términos",
                "partial_template": "applications/partials/wizard_step_5.html",
            },
        ]

        return context


class ApplicationUploadView(LoginRequiredMixin, View):
    """Handle file uploads for application attachments."""

    TIPO_MAP = {
        "cedula": Anexo.TipoAnxo.CEDULA,
        "certificado_notas": Anexo.TipoAnxo.CERTIFICADO_NOTAS,
        "diploma": Anexo.TipoAnxo.DIPLOMA,
        "recibo_pago": Anexo.TipoAnxo.RECIBO_PAGO,
    }

    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_TYPES = ["application/pdf", "image/jpeg", "image/png"]

    def post(self, request, *args, **kwargs):
        """Handle file upload via AJAX."""
        uuid = kwargs.get("pk")
        application = get_object_or_404(
            Solicitud.objects.filter(aspirante=self.request.user),
            uuid=uuid
        )

        # Check file
        uploaded_file = request.FILES.get("file")
        if not uploaded_file:
            return JsonResponse({"success": False, "error": "No file provided"}, status=400)

        # Validate size
        if uploaded_file.size > self.MAX_SIZE:
            return JsonResponse({"success": False, "error": "File exceeds 10MB limit"}, status=400)

        # Validate type
        if uploaded_file.content_type not in self.ALLOWED_TYPES:
            return JsonResponse({"success": False, "error": "Invalid file type. PDF, JPG, PNG only."}, status=400)

        # Get file type from form
        file_type = request.POST.get("file_type", "otro")
        tipo_anexo = self.TIPO_MAP.get(file_type, Anexo.TipoAnxo.OTRO)

        # Calculate SHA256
        file_hash = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            file_hash.update(chunk)
        sha256 = file_hash.hexdigest()

        # Create Anexo
        anexo = Anexo.objects.create(
            solicitud=application,
            tipo_anexo=tipo_anexo,
            archivo=uploaded_file,
            nombre_original=uploaded_file.name,
            tamano=uploaded_file.size,
            mime_type=uploaded_file.content_type,
            sha256=sha256,
        )

        return JsonResponse({
            "success": True,
            "anexo_id": anexo.id,
            "nombre": anexo.nombre_original,
            "tipo": anexo.get_tipo_anexo_display(),
            "url": anexo.archivo.url,
        })


# =============================================================================
# Requirement Review Views (CHG-203)
# =============================================================================

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.views.generic import DetailView, ListView, UpdateView

User = get_user_model()


def has_revisor_role(user):
    """Check if user has R-REVISOR role."""
    return user.groups.filter(name="R-REVISOR").exists()


class RequirementReviewListView(LoginRequiredMixin, ReviewerPermissionMixin, ListView):
    """List view for requirements review (R-REVISOR role)."""

    model = Solicitud
    template_name = "applications/review/list.html"
    context_object_name = "solicitudes"

    def get_queryset(self):
        """Return solicitudes in verification state."""
        # Only show solicitudes that need review
        return Solicitud.objects.filter(
            estado__in=[Solicitud.Estado.RADICADA, Solicitud.Estado.EN_VERIFICACION]
        ).select_related(
            "convocatoria",
            "aspirante"
        ).order_by("-created_at")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Calculate progress for each solicitud
        for solicitud in context["solicitudes"]:
            total = solicitud.validaciones.count()
            verificadas = solicitud.validaciones.filter(
                estado=RequisitoValidacion.Estado.VERIFICADO
            ).count()
            solicitud.progress = int((verificadas / total * 100) if total > 0 else 0)
        return context


class RequirementReviewDetailView(LoginRequiredMixin, ReviewerPermissionMixin, DetailView):
    """Detail view for requirement verification."""

    model = Solicitud
    template_name = "applications/review/detail.html"
    context_object_name = "solicitud"

    def get_object(self, queryset=None):
        """Get solicitud by UUID."""
        uuid = self.kwargs.get("pk")
        return get_object_or_404(Solicitud, uuid=uuid)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        solicitud = context["solicitud"]

        # Get or create validaciones for this solicitud
        # First check if we have validaciones, if not, create from config
        if not solicitud.validaciones.exists():
            # Try to get requisitos from convocatoria config
            try:
                config = solicitud.convocatoria.configuracion
                requisitos = config.get("requisitos", [])

                for req in requisitos:
                    RequisitoValidacion.objects.get_or_create(
                        solicitud=solicitud,
                        requisito_code=req.get("code", ""),
                        defaults={
                            "requisito_nombre": req.get("name", ""),
                        }
                    )
            except Exception:
                # If no config, create default requisitos
                default_requisitos = [
                    {"code": "r1", "name": "Verificar SNIES"},
                    {"code": "r2", "name": "Verificar SISBÉN"},
                    {"code": "r3", "name": "Verificar documento de identidad"},
                    {"code": "r4", "name": "Verificar certificado de notas"},
                    {"code": "r5", "name": "Verificar situación socioeconómica"},
                    {"code": "r6", "name": "Verificar no reciben otro beneficio"},
                    {"code": "r7", "name": "Verificar requisitos de convocatoria"},
                ]
                for req in default_requisitos:
                    RequisitoValidacion.objects.get_or_create(
                        solicitud=solicitud,
                        requisito_code=req["code"],
                        defaults={"requisito_nombre": req["name"]}
                    )

        # Get validaciones
        context["validaciones"] = solicitud.validaciones.all()

        # Calculate progress
        total = solicitud.validaciones.count()
        verificadas = solicitud.validaciones.filter(
            estado=RequisitoValidacion.Estado.VERIFICADO
        ).count()
        rechazadas = solicitud.validaciones.filter(
            estado=RequisitoValidacion.Estado.RECHAZADO
        ).count()

        context["progress"] = {
            "total": total,
            "verificadas": verificadas,
            "rechazadas": rechazadas,
            "pendientes": total - verificadas - rechazadas,
            "porcentaje": int((verificadas / total * 100) if total > 0 else 0),
        }

        context["can_approve"] = verificadas == total and total > 0
        context["can_reject"] = rechazadas > 0

        return context


class RequirementVerifyView(LoginRequiredMixin, UpdateView):
    """Handle requirement verification via AJAX."""

    model = RequisitoValidacion
    fields = ["estado", "evidencia", "observaciones"]

    def post(self, request, *args, **kwargs):
        """Handle verification update."""
        validacion = self.get_object()

        # Get data from POST
        estado = request.POST.get("estado")
        observaciones = request.POST.get("observaciones", "")

        # Update validacion
        validacion.estado = estado
        validacion.observaciones = observaciones
        validacion.validado_por = request.user
        validacion.fecha_validacion = timezone.now()

        # Handle file upload for evidence
        evidencia = request.FILES.get("evidencia")
        if evidencia:
            validacion.evidencia = evidencia

        validacion.save()

        # Update solicitud state if needed
        solicitud = validacion.solicitud

        # Check all validaciones
        verificadas = solicitud.validaciones.filter(
            estado=RequisitoValidacion.Estado.VERIFICADO
        ).count()
        total = solicitud.validaciones.count()

        if verificadas == total and total > 0:
            solicitud.estado = Solicitud.Estado.VERIFICADA
            solicitud.save()

        return JsonResponse({
            "success": True,
            "validacion_id": validacion.id,
            "estado": validacion.estado,
        })


class RequirementApproveView(LoginRequiredMixin, View):
    """Approve all requirements for a solicitud."""

    def post(self, request, *args, **kwargs):
        uuid = kwargs.get("pk")
        solicitud = get_object_or_404(Solicitud, uuid=uuid)

        # Mark all as verified
        solicitud.validaciones.filter(
            estado=RequisitoValidacion.Estado.PENDIENTE
        ).update(
            estado=RequisitoValidacion.Estado.VERIFICADO,
            validado_por=request.user,
            fecha_validacion=timezone.now(),
        )

        # Update solicitud state
        solicitud.estado = Solicitud.Estado.VERIFICADA
        solicitud.save()

        # Send notification to applicant
        try:
            from apps.accounts.services.notifications import InAppNotifier
            notifier = InAppNotifier()
            notifier.notify(
                user=solicitud.aspirante,
                event="solicitud.verificada",
                payload={
                    "radicado": solicitud.radicado,
                    "convocatoria": solicitud.convocatoria.nombre,
                }
            )
        except Exception:
            pass  # Notification failure should not block

        messages.success(request, "Solicitud aprobada - todos los requisitos verificados")

        return JsonResponse({
            "success": True,
            "redirect": reverse("applications:review_list"),
        })


class RequirementRejectView(LoginRequiredMixin, View):
    """Reject a solicitud."""

    def post(self, request, *args, **kwargs):
        uuid = kwargs.get("pk")
        solicitud = get_object_or_404(Solicitud, uuid=uuid)

        # Mark solicitud as rejected
        solicitud.estado = Solicitud.Estado.RECHAZADA
        solicitud.save()

        # Send notification to applicant
        try:
            from apps.accounts.services.notifications import InAppNotifier
            notifier = InAppNotifier()
            notifier.notify(
                user=solicitud.aspirante,
                event="solicitud.rechazada",
                payload={
                    "radicado": solicitud.radicado,
                    "convocatoria": solicitud.convocatoria.nombre,
                }
            )
        except Exception:
            pass  # Notification failure should not block

        messages.error(request, "Solicitud rechazada")

        return JsonResponse({
            "success": True,
            "redirect": reverse("applications:review_list"),
        })


class RequirementHistoryView(LoginRequiredMixin, DetailView):
    """View history of verifications for a solicitud."""

    model = Solicitud
    template_name = "applications/review/history.html"
    context_object_name = "solicitud"

    def dispatch(self, request, *args, **kwargs):
        """Check if user has R-REVISOR role."""
        if not has_revisor_role(request.user) and not request.user.is_superuser:
            messages.error(request, "No tienes permiso para acceder a esta sección.")
            return redirect("dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        """Get solicitud by UUID."""
        uuid = self.kwargs.get("pk")
        return get_object_or_404(Solicitud, uuid=uuid)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        solicitud = context["solicitud"]

        # Get all validaciones ordered by date
        context["validaciones"] = solicitud.validaciones.order_by("-updated_at")

        # Get state changes
        context["estado_historial"] = []
        # This would typically come from AuditEvent
        # For now, we'll use the created_at and updated_at from validaciones

        return context
