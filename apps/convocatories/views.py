"""Views for Convocatory management."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.accounts.permissions_mixin import PermissionMixin, AdminPermissionMixin
from apps.convocatories.models import Convocatory
from apps.convocatories.services.convocatoria_service import (
    transicionar_estado,
)


class ConvocatoryViewMixin(LoginRequiredMixin, PermissionMixin, TemplateView):
    """Base view for any convocatory page - any authenticated user can view."""

    login_url = reverse_lazy("login")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["convocatory_section"] = True
        return context


class BaseConvocatoryView(ConvocatoryViewMixin, AdminPermissionMixin):
    """Base view for admin/coordinator actions on convocatories."""
    pass


class ConvocatoryListView(ConvocatoryViewMixin):
    """List all public convocatories - any authenticated user can view."""

    template_name = "convocatories/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get filters
        search = self.request.GET.get("search", "")
        estado_filter = self.request.GET.get("estado", "")
        tipo_filter = self.request.GET.get("tipo", "")

        # Base queryset
        convocatories = Convocatory.objects.all().order_by("-created_at")

        # Apply filters
        if search:
            convocatories = convocatories.filter(
                Q(nombre__icontains=search) | Q(codigo__icontains=search)
            )

        if estado_filter:
            convocatories = convocatories.filter(estado=estado_filter)

        if tipo_filter:
            convocatories = convocatories.filter(tipo=tipo_filter)

        context["convocatories"] = convocatories
        context["search"] = search
        context["estado_filter"] = estado_filter
        context["tipo_filter"] = tipo_filter
        context["estados"] = Convocatory.Estado.choices
        context["tipos"] = Convocatory.Tipo.choices

        return context


class ConvocatoryCreateView(BaseConvocatoryView):
    """Create a new convocatory."""

    template_name = "convocatories/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["action"] = "crear"
        context["tipos"] = Convocatory.Tipo.choices
        return context

    def post(self, request, *args, **kwargs):
        nombre = request.POST.get("nombre", "").strip()
        codigo = request.POST.get("codigo", "").strip()
        tipo = request.POST.get("tipo", Convocatory.Tipo.PUBLICA)
        periodo = request.POST.get("periodo", "").strip()
        monto = request.POST.get("monto_semestre_smlmv", "5")
        duracion = request.POST.get("duracion_maxima_semestres", "4")
        cupo = request.POST.get("cupo_total", "100")

        # Validation
        errors = []
        if not nombre:
            errors.append("El nombre es requerido.")
        if not codigo:
            errors.append("El código es requerido.")
        elif Convocatory.objects.filter(codigo=codigo).exists():
            errors.append("Ya existe una convocatoria con ese código.")
        if not periodo:
            errors.append("El período es requerido.")

        if errors:
            for error in errors:
                messages.error(request, error)
            return redirect("convocatories:create")

        # Create
        Convocatory.objects.create(
            nombre=nombre,
            codigo=codigo,
            tipo=tipo,
            periodo=periodo,
            monto_semestre_smlmv=monto,
            duracion_maxima_semestres=duracion,
            cupo_total=cupo,
            estado=Convocatory.Estado.BORRADOR,
        )

        messages.success(request, f"Convocatoria {nombre} creada exitosamente.")
        return redirect("convocatories:list")


class ConvocatoryUpdateView(BaseConvocatoryView):
    """Update a convocatory (only in draft state)."""

    template_name = "convocatories/form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        convocatory = get_object_or_404(Convocatory, pk=pk)

        if convocatory.estado != Convocatory.Estado.BORRADOR:
            messages.error(
                self.request,
                "Solo se pueden editar convocatorias en estado borrador.",
            )
            return redirect("convocatories:detail", pk=pk)

        context["action"] = "editar"
        context["convocatory"] = convocatory
        context["tipos"] = Convocatory.Tipo.choices
        return context

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        convocatory = get_object_or_404(Convocatory, pk=pk)

        if convocatory.estado != Convocatory.Estado.BORRADOR:
            messages.error(
                request, "Solo se pueden editar convocatorias en estado borrador."
            )
            return redirect("convocatories:detail", pk=pk)

        # Update fields
        convocatory.nombre = request.POST.get("nombre", "").strip()
        convocatory.tipo = request.POST.get("tipo", Convocatory.Tipo.PUBLICA)
        convocatory.periodo = request.POST.get("periodo", "").strip()
        convocatory.monto_semestre_smlmv = request.POST.get(
            "monto_semestre_smlmv", "5"
        )
        convocatory.duracion_maxima_semestres = request.POST.get(
            "duracion_maxima_semestres", "4"
        )
        convocatory.cupo_total = request.POST.get("cupo_total", "100")
        convocatory.save()

        messages.success(request, "Convocatoria actualizada exitosamente.")
        return redirect("convocatories:detail", pk=pk)


class ConvocatoryDetailView(ConvocatoryViewMixin):
    """View convocation detail - any authenticated user can view."""

    template_name = "convocatories/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        pk = self.kwargs.get("pk")
        convocatory = get_object_or_404(Convocatory, pk=pk)

        context["convocatory"] = convocatory

        # Available transitions (only for managers) - using can_manage from PermissionMixin
        if context["can_manage"]:
            transitions = {
                Convocatory.Estado.BORRADOR: ["publicar"],
                Convocatory.Estado.PUBLICADA: ["abrir_inscripciones"],
                Convocatory.Estado.EN_INSCRIPCION: ["cerrar_inscripciones"],
                Convocatory.Estado.EN_VERIFICACION: ["iniciar_calificacion"],
                Convocatory.Estado.EN_CALIFICACION: ["publicar_resultados"],
                Convocatory.Estado.DEFINITIVA: ["cerrar"],
            }
            context["available_transitions"] = transitions.get(convocatory.estado, [])
        else:
            context["available_transitions"] = []

        return context


class ConvocatoryTransitionView(BaseConvocatoryView):
    """Handle state transitions."""

    def post(self, request, *args, **kwargs):
        pk = self.kwargs.get("pk")
        transition = request.POST.get("transition")

        convocatory = get_object_or_404(Convocatory, pk=pk)

        # Map transition names to estado values
        transition_map = {
            "publicar": "publicada",
            "abrir_inscripciones": "en_inscripcion",
            "cerrar_inscripciones": "en_verificacion",
            "iniciar_calificacion": "en_calificacion",
            "publicar_resultados": "definitiva",
            "cerrar": "cerrada",
        }

        estado_destino = transition_map.get(transition)
        if not estado_destino:
            messages.error(request, f"Transición '{transition}' no válida.")
            return redirect("convocatories:detail", pk=pk)

        # Check permissions for close transition
        if transition == "cerrar":
            has_admin = request.user.user_roles.filter(
                role__code="R-ADMIN"
            ).exists()
            is_superuser = request.user.is_superuser
            if not (has_admin or is_superuser):
                messages.error(
                    request, "Solo R-ADMIN puede cerrar una convocatoria."
                )
                return redirect("convocatories:detail", pk=pk)

        try:
            transicionar_estado(convocatory, estado_destino, request.user)
            messages.success(
                request, f"Convocatoria movida a '{transition}' exitosamente."
            )
        except Exception as e:
            messages.error(request, str(e))

        return redirect("convocatories:detail", pk=pk)
