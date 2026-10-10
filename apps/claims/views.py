"""HTML views for claims (CHG-205)."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.accounts.permissions_mixin import (
    PermissionMixin,
)
from apps.applications.models import Solicitud
from apps.claims.models import Apelacion, Reclamacion
from apps.claims.services import (
    crear_reclamacion,
    resolver_reclamacion,
)


class ReclamacionPermissionMixin(PermissionMixin):
    """Mixin for claim-specific permissions."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Check ownership or junta role
        user = self.request.user
        if user == obj.solicitud.aspirante:
            return obj
        # Check if user is junta
        if self._has_role(user, "R-JUNTA"):
            return obj
        if user.is_superuser:
            return obj
        raise PermissionError("No tienes permiso para ver esta reclamación")


class ReclamacionListView(LoginRequiredMixin, PermissionMixin, ListView):
    """List claims for the current user."""

    model = Reclamacion
    template_name = "claims/list.html"
    context_object_name = "reclamaciones"
    paginate_by = 10

    def get_queryset(self):
        return Reclamacion.objects.filter(solicitud__aspirante=self.request.user).select_related(
            "solicitud", "solicitud__convocatoria"
        )


class ReclamacionCreateView(LoginRequiredMixin, CreateView):
    """Create a new claim for a solicitud."""

    model = Reclamacion
    fields = ["tipo", "descripcion", "evidencia"]
    template_name = "claims/create.html"

    def get_success_url(self):
        return reverse_lazy("claims:detail", kwargs={"pk": self.object.uuid})

    def get_initial(self):
        initial = super().get_initial()
        solicitud_uuid = self.kwargs.get("solicitud_uuid")
        if solicitud_uuid:
            initial["solicitud_uuid"] = solicitud_uuid
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        solicitud_uuid = self.kwargs.get("solicitud_uuid")
        if solicitud_uuid:
            context["solicitud"] = get_object_or_404(Solicitud, uuid=solicitud_uuid)
        return context

    def form_valid(self, form):
        solicitud_uuid = self.kwargs.get("solicitud_uuid")
        solicitud = get_object_or_404(Solicitud, uuid=solicitud_uuid)

        # Verify ownership
        if solicitud.aspirante != self.request.user:
            messages.error(
                self.request, "Solo puedes presentar reclamaciones para tus propias postulaciones."
            )
            return redirect("claims:list")

        # Verify solicitud can be claimed (must be in valid state)
        if solicitud.estado not in [
            Solicitud.Estado.VERIFICADA,
            Solicitud.Estado.RADICADA,
        ]:
            messages.error(self.request, "No puedes presentar reclamación para esta postulación.")
            return redirect("claims:list")

        # Create the claim
        try:
            reclamacion = crear_reclamacion(
                solicitud=solicitud,
                tipo=form.cleaned_data["tipo"],
                descripcion=form.cleaned_data["descripcion"],
                evidencia=form.cleaned_data.get("evidencia"),
                actor=self.request.user,
            )
            messages.success(self.request, "Reclamación presentada exitosamente.")
            return redirect(reverse_lazy("claims:detail", kwargs={"pk": reclamacion.uuid}))
        except Exception as e:
            messages.error(self.request, str(e))
            return redirect("claims:list")


class ReclamacionDetailView(LoginRequiredMixin, DetailView):
    """View claim details."""

    model = Reclamacion
    template_name = "claims/detail.html"
    context_object_name = "reclamacion"
    pk_url_kwarg = "pk"

    def get_queryset(self):
        return Reclamacion.objects.select_related(
            "solicitud",
            "solicitud__convocatoria",
            "resuelto_por",
        ).prefetch_related("historial")

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user

        # Owner, junta, or admin
        if user == obj.solicitud.aspirante or user.is_superuser or self._has_junta_role(user):
            return obj

        raise PermissionError("No tienes permiso para ver esta reclamación")

    def _has_junta_role(self, user):
        from apps.accounts.models import Role

        junta = Role.objects.filter(code="R-JUNTA").first()
        return bool(junta and user.userrole_set.filter(role=junta).exists())


class ReclamacionUpdateView(LoginRequiredMixin, UpdateView):
    """Update a claim (only if PRESENTADA)."""

    model = Reclamacion
    fields = ["descripcion", "evidencia"]
    template_name = "claims/edit.html"
    pk_url_kwarg = "pk"

    def get_success_url(self):
        return reverse_lazy("claims:detail", kwargs={"pk": self.object.uuid})

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)

        # Must be owner
        if obj.solicitud.aspirante != self.request.user:
            raise PermissionError("No tienes permiso para editar esta reclamación")

        # Must be in PRESENTADA state
        if obj.estado != Reclamacion.Estado.PRESENTADA:
            messages.error(self.request, "Solo puedes editar reclamaciones en estado PRESENTADA.")
            return redirect("claims:detail", pk=obj.uuid)

        return obj

    def form_valid(self, form):
        messages.success(self.request, "Reclamación actualizada.")
        return super().form_valid(form)


class ReclamacionAdminListView(LoginRequiredMixin, TemplateView):
    """Admin list view for claims (Junta)."""

    template_name = "claims/admin/list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check permissions
        user = self.request.user
        if not (user.is_superuser or self._has_junta_role(user)):
            messages.error(self.request, "Solo R-JUNTA puede acceder a esta página.")
            return context

        context["reclamaciones"] = Reclamacion.objects.select_related(
            "solicitud",
            "solicitud__convocatoria",
            "solicitud__aspirante",
        ).order_by("-created_at")

        return context

    def _has_junta_role(self, user):
        from apps.accounts.models import Role

        junta = Role.objects.filter(code="R-JUNTA").first()
        return bool(junta and user.userrole_set.filter(role=junta).exists())


class ReclamacionResolveView(LoginRequiredMixin, View):
    """Resolve a claim (Junta action)."""

    def post(self, request, *args, **kwargs):
        reclamacion = get_object_or_404(
            Reclamacion.objects.select_related("solicitud"), uuid=kwargs.get("pk")
        )

        # Check permissions
        user = request.user
        if not (user.is_superuser or self._has_junta_role(user)):
            messages.error(request, "Solo R-JUNTA puede resolver reclamaciones.")
            return redirect("claims:admin_list")

        # Must be in EN_REVISION state
        if reclamacion.estado != Reclamacion.Estado.EN_REVISION:
            messages.error(request, "Solo puedes resolver reclamaciones en revisión.")
            return redirect("claims:admin_detail", pk=reclamacion.uuid)

        # Get action
        accion = request.POST.get("accion", "rechazar")
        respuesta = request.POST.get("respuesta", "")

        if not respuesta:
            messages.error(request, "Debes proporcionar una respuesta.")
            return redirect("claims:admin_detail", pk=reclamacion.uuid)

        aceptar = accion == "aceptar"

        try:
            resolver_reclamacion(
                reclamacion=reclamacion,
                respuesta=respuesta,
                aceptar=aceptar,
                actor=user,
            )
            messages.success(
                request, f"Reclamación {'aceptada' if aceptar else 'rechazada'} exitosamente."
            )
        except Exception as e:
            messages.error(request, str(e))

        return redirect("claims:admin_list")

    def _has_junta_role(self, user):
        from apps.accounts.models import Role

        junta = Role.objects.filter(code="R-JUNTA").first()
        return bool(junta and user.userrole_set.filter(role=junta).exists())


# ============================================================================
# Apelacion Views (CHG-206)
# ============================================================================


class ApelacionPermissionMixin:
    """Mixin for appeal-specific permissions."""

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user

        # Check if user is the titular
        if user == obj.reclamacion.solicitud.aspirante:
            return obj

        # Check if user has OFIJUR role
        if self._has_ofijur_role(user):
            return obj

        # Check if user is superuser
        if user.is_superuser:
            return obj

        raise PermissionError("No tienes permiso para ver esta apelación.")

    def _has_ofijur_role(self, user):
        from apps.accounts.models import Role

        ofijur = Role.objects.filter(code="R-OFIJUR").first()
        return bool(ofijur and user.userrole_set.filter(role=ofijur).exists())


class ApelacionListView(LoginRequiredMixin, ListView):
    """List appeals for the current user."""

    model = Apelacion
    template_name = "claims/apelacion_list.html"
    context_object_name = "apelaciones"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user

        # If user has OFIJUR role, show all appeals
        if self._has_ofijur_role(user) or user.is_superuser:
            return Apelacion.objects.select_related(
                "reclamacion",
                "reclamacion__solicitud",
                "reclamacion__solicitud__convocatoria",
            ).order_by("-created_at")

        # Otherwise, show only user's appeals
        return (
            Apelacion.objects.filter(reclamacion__solicitud__aspirante=user)
            .select_related(
                "reclamacion",
                "reclamacion__solicitud",
                "reclamacion__solicitud__convocatoria",
            )
            .order_by("-created_at")
        )

    def _has_ofijur_role(self, user):
        from apps.accounts.models import Role

        ofijur = Role.objects.filter(code="R-OFIJUR").first()
        return bool(ofijur and user.userrole_set.filter(role=ofijur).exists())


class ApelacionCreateView(LoginRequiredMixin, CreateView):
    """Create a new appeal for a resolved claim."""

    model = Apelacion
    fields = ["descripcion", "evidencia"]
    template_name = "claims/apelacion_create.html"

    def get_success_url(self):
        return reverse_lazy("claims:apelacion_detail", kwargs={"pk": self.object.uuid})

    def get_initial(self):
        initial = super().get_initial()
        reclamacion_uuid = self.kwargs.get("reclamacion_uuid")
        if reclamacion_uuid:
            initial["reclamacion_uuid"] = reclamacion_uuid
        return initial

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        reclamacion_uuid = self.kwargs.get("reclamacion_uuid")
        if reclamacion_uuid:
            from apps.claims.models import Reclamacion

            context["reclamacion"] = get_object_or_404(Reclamacion, uuid=reclamacion_uuid)
        return context

    def form_valid(self, form):
        reclamacion_uuid = self.kwargs.get("reclamacion_uuid")
        reclamacion = get_object_or_404(Reclamacion, uuid=reclamacion_uuid)

        # Verify ownership and preconditions
        if reclamacion.solicitud.aspirante != self.request.user:
            messages.error(
                self.request, "Solo puedes presentar apelaciones para tus propias reclamaciones."
            )
            return redirect("claims:list")

        # Use the service to create the appeal with validation
        from apps.claims.services.apelaciones import create_apelacion

        try:
            apelacion = create_apelacion(
                reclamacion=reclamacion,
                descripcion=form.cleaned_data["descripcion"],
                evidencia=form.cleaned_data.get("evidencia"),
                actor=self.request.user,
            )

            # Set the object for the view
            self.object = apelacion

            messages.success(self.request, "Apelación presentada exitosamente.")
            return redirect(self.get_success_url())

        except Exception as e:
            messages.error(self.request, str(e))
            return self.form_invalid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Por favor corrige los errores en el formulario.")
        return super().form_invalid(form)


class ApelacionDetailView(LoginRequiredMixin, ApelacionPermissionMixin, DetailView):
    """View details of an appeal."""

    model = Apelacion
    template_name = "claims/apelacion_detail.html"
    context_object_name = "apelacion"
    pk_url_kwarg = "pk"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["historial"] = self.object.historial.all().order_by("created_at")
        context["can_transition"] = self._has_ofijur_role(self.request.user)
        return context

    def _has_ofijur_role(self, user):
        from apps.accounts.models import Role

        ofijur = Role.objects.filter(code="R-OFIJUR").first()
        return bool(ofijur and user.userrole_set.filter(role=ofijur).exists())


class ApelacionTransitionView(LoginRequiredMixin, View):
    """Handle state transitions for appeals (OFIJUR actions)."""

    def post(self, request, *args, **kwargs):
        apelacion = get_object_or_404(
            Apelacion.objects.select_related("reclamacion", "reclamacion__solicitud"),
            uuid=kwargs.get("pk"),
        )

        # Check OFIJUR permissions
        user = request.user
        if not (user.is_superuser or self._has_ofijur_role(user)):
            messages.error(request, "Solo R-OFIJUR puede realizar transiciones.")
            return redirect("claims:apelacion_detail", pk=apelacion.uuid)

        # Get action and respuesta
        accion = request.POST.get("accion", "")
        respuesta = request.POST.get("respuesta", "")

        if not accion:
            messages.error(request, "Acción no especificada.")
            return redirect("claims:apelacion_detail", pk=apelacion.uuid)

        try:
            from apps.claims.services.transitions import (
                confirmar,
                iniciar_analisis,
                revocar,
            )

            if accion == "iniciar_analisis":
                iniciar_analisis(apelacion, user)
                messages.success(request, "Análisis iniciado exitosamente.")

            elif accion == "confirmar":
                if not respuesta:
                    messages.error(request, "Debes proporcionar una respuesta.")
                    return redirect("claims:apelacion_detail", pk=apelacion.uuid)
                confirmar(apelacion, respuesta, user)
                messages.success(request, "Apelación confirmada exitosamente.")

            elif accion == "revocar":
                if not respuesta:
                    messages.error(request, "Debes proporcionar una respuesta.")
                    return redirect("claims:apelacion_detail", pk=apelacion.uuid)
                revocar(apelacion, respuesta, user)
                messages.success(request, "Apelación revocada exitosamente.")

            else:
                messages.error(request, f"Acción no reconocida: {accion}")

        except Exception as e:
            messages.error(request, str(e))

        return redirect("claims:apelacion_detail", pk=apelacion.uuid)

    def _has_ofijur_role(self, user):
        from apps.accounts.models import Role

        ofijur = Role.objects.filter(code="R-OFIJUR").first()
        return bool(ofijur and user.userrole_set.filter(role=ofijur).exists())


class ApelacionAdminListView(LoginRequiredMixin, TemplateView):
    """Admin list view for appeals (OFIJUR)."""

    template_name = "claims/apelacion_admin_list.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check OFIJUR permissions
        user = self.request.user
        if not (user.is_superuser or self._has_ofijur_role(user)):
            messages.error(self.request, "Solo R-OFIJUR puede acceder a esta página.")
            return context

        context["apelaciones"] = Apelacion.objects.select_related(
            "reclamacion",
            "reclamacion__solicitud",
            "reclamacion__solicitud__convocatoria",
            "reclamacion__solicitud__aspirante",
        ).order_by("-created_at")

        return context

    def _has_ofijur_role(self, user):
        from apps.accounts.models import Role

        ofijur = Role.objects.filter(code="R-OFIJUR").first()
        return bool(ofijur and user.userrole_set.filter(role=ofijur).exists())
