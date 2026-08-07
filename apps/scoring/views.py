"""HTML views for scoring (CHG-204)."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import ListView, DetailView, UpdateView, TemplateView

from apps.accounts.permissions_mixin import PermissionMixin, CommitteePermissionMixin
from apps.applications.models import Solicitud
from apps.scoring.models import Evaluacion, PuntajeTotal
from apps.scoring.services.scoring_service import (
    calcular_puntaje_total,
    generar_rankings_completos,
    create_default_evaluaciones,
    DEFAULT_WEIGHTS,
)


def has_comite_role(user):
    """Check if user has R-COMITE role."""
    return user.groups.filter(name="R-COMITE").exists()


class ScoringListView(LoginRequiredMixin, CommitteePermissionMixin, ListView):
    """List view for scoring (verified applications pending evaluation)."""
    
    model = Solicitud
    template_name = "scoring/list.html"
    context_object_name = "solicitudes"
    
    def get_queryset(self):
        """Return verified solicitudes that need scoring."""
        return Solicitud.objects.filter(
            estado=Solicitud.Estado.VERIFICADA
        ).select_related(
            "convocatoria",
            "aspirante"
        ).order_by("-created_at")
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add scoring progress for each solicitud
        for solicitud in context["solicitudes"]:
            total = solicitud.evaluaciones.count()
            evaluadas = solicitud.evaluaciones.exclude(puntaje__isnull=True).count()
            solicitud.progress = int((evaluadas / total * 100) if total > 0 else 0)
            
            # Get puntaje total if exists
            try:
                solicitud.puntaje = solicitud.puntaje_total.puntaje_total
            except PuntajeTotal.DoesNotExist:
                solicitud.puntaje = None
        
        return context


class ScoringDetailView(LoginRequiredMixin, CommitteePermissionMixin, DetailView):
    """Detail view for scoring an application."""
    
    model = Solicitud
    template_name = "scoring/detail.html"
    context_object_name = "solicitud"
    
    def get_object(self, queryset=None):
        """Get solicitud by UUID."""
        uuid = self.kwargs.get("solicitud_pk")
        return get_object_or_404(Solicitud, uuid=uuid)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        solicitud = context["solicitud"]
        
        # Create default evaluaciones if they don't exist
        if not solicitud.evaluaciones.exists():
            create_default_evaluaciones(solicitud)
        
        # Get evaluaciones
        context["evaluaciones"] = solicitud.evaluaciones.all()
        context["weights"] = DEFAULT_WEIGHTS
        
        # Get puntaje total if exists
        try:
            context["puntaje_total"] = solicitud.puntaje_total
        except PuntajeTotal.DoesNotExist:
            context["puntaje_total"] = None
        
        return context


class ScoringEvaluateView(LoginRequiredMixin, UpdateView):
    """Handle criterion evaluation via AJAX."""
    
    model = Evaluacion
    fields = ["puntaje", "observaciones"]
    
    def get_object(self, queryset=None):
        """Get evaluacion by ID."""
        evaluacion_pk = self.kwargs.get("evaluacion_pk")
        return get_object_or_404(Evaluacion, id=evaluacion_pk)
    
    def post(self, request, *args, **kwargs):
        """Handle evaluation update."""
        evaluacion = self.get_object()
        
        # Get data from POST
        puntaje = request.POST.get("puntaje")
        observaciones = request.POST.get("observaciones", "")
        
        # Update evaluacion
        if puntaje:
            evaluacion.puntaje = puntaje
        evaluacion.observaciones = observaciones
        evaluacion.evaluado_por = request.user
        evaluacion.save()
        
        # Recalculate total score
        calcular_puntaje_total(evaluacion.solicitud, request.user)
        
        return JsonResponse({
            "success": True,
            "evaluacion_id": evaluacion.id,
            "puntaje": str(evaluacion.puntaje),
        })


class ScoringCalculateView(LoginRequiredMixin, View):
    """Calculate total scores for a solicitud."""
    
    def post(self, request, *args, **kwargs):
        uuid = kwargs.get("solicitud_pk")
        solicitud = get_object_or_404(Solicitud, uuid=uuid)
        
        # Calculate total
        puntaje = calcular_puntaje_total(solicitud, request.user)
        
        messages.success(request, f"Puntaje total calculado: {puntaje.puntaje_total}")
        
        return JsonResponse({
            "success": True,
            "puntaje_total": str(puntaje.puntaje_total),
        })


class RankingView(LoginRequiredMixin, TemplateView):
    """Ranking view for scoring results."""
    
    template_name = "scoring/ranking.html"
    
    def dispatch(self, request, *args, **kwargs):
        """Check if user has R-COMITE or R-COORDINADOR role."""
        has_access = (
            has_comite_role(request.user) or
            request.user.groups.filter(name="R-COORDINADOR").exists() or
            request.user.is_superuser
        )
        if not has_access:
            messages.error(request, "No tienes permiso para acceder a esta sección.")
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all puntajes with rankings
        puntajes = PuntajeTotal.objects.filter(
            solicitud__estado=Solicitud.Estado.VERIFICADA
        ).select_related(
            "solicitud",
            "solicitud__convocatoria",
            "solicitud__aspirante"
        ).order_by("ranking_general")
        
        context["puntajes"] = puntajes
        
        # Group by municipality
        by_municipio = {}
        for p in puntajes:
            mun = p.solicitud.datos_personales.get("municipio", "desconocido")
            if mun not in by_municipio:
                by_municipio[mun] = []
            by_municipio[mun].append(p)
        
        context["by_municipio"] = by_municipio
        
        return context


class RankingGenerateView(LoginRequiredMixin, View):
    """Generate rankings for a convocatoria."""
    
    def post(self, request, *args, **kwargs):
        from apps.convocatories.models import Convocatory
        
        convocatoria_id = request.POST.get("convocatoria_id")
        convocatoria = get_object_or_404(Convocatory, id=convocatoria_id)
        
        # Generate rankings
        result = generar_rankings_completos(convocatoria)
        
        messages.success(request, "Rankings generados correctamente")
        
        return JsonResponse({
            "success": True,
            "result": result,
        })


class ScoringExportView(LoginRequiredMixin, View):
    """Export scoring results."""
    
    def get(self, request, *args, **kwargs):
        from django.http import HttpResponse
        import csv
        
        # Get all puntajes
        puntajes = PuntajeTotal.objects.filter(
            solicitud__estado=Solicitud.Estado.VERIFICADA
        ).select_related(
            "solicitud",
            "solicitud__convocatoria",
            "solicitud__aspirante"
        ).order_by("ranking_general")
        
        # Create CSV response
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="ranking.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            "Ranking",
            "Radicado",
            "Aspirante",
            "Municipio",
            "Puntaje Socioeconómico",
            "Puntaje Académico",
            "Puntaje Excelencia",
            "Puntaje Total",
        ])
        
        for p in puntajes:
            writer.writerow([
                p.ranking_general,
                p.solicitud.radicado,
                f"{p.solicitud.aspirante.first_name} {p.solicitud.aspirante.last_name}",
                p.solicitud.datos_personales.get("municipio", ""),
                p.puntaje_socioeconomico,
                p.puntaje_academico,
                p.puntaje_excelencia,
                p.puntaje_total,
            ])
        
        return response
