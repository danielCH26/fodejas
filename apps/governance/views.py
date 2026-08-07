"""HTML views for governance app (CHG-207)."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.accounts.permissions_mixin import PermissionMixin, JuntaPermissionMixin
from apps.convocatories.models import Convocatory
from apps.governance.models import ActoAdministrativo, ListadoDefinitivo
from apps.governance.services import (
    generar_listado_definitivo,
    generar_numero_acto,
    guardar_pdf_acto,
    obtener_ranking_final,
)


class ActoListView(JuntaPermissionMixin, ListView):
    """List all administrative acts."""

    model = ActoAdministrativo
    template_name = "governance/acto_list.html"
    context_object_name = "actos"
    paginate_by = 10

    def get_queryset(self):
        return ActoAdministrativo.objects.select_related("convocatoria").order_by("-created_at")


class ActoCreateView(JuntaPermissionMixin, CreateView):
    """Create a new administrative act."""

    model = ActoAdministrativo
    fields = ["tipo", "fecha_expedicion", "asunto", "considerandos", "resolutivo", "convocatoria", "firmantes"]
    template_name = "governance/acto_create.html"

    def get_success_url(self):
        return reverse_lazy("governance:acto_detail", kwargs={"pk": self.object.uuid})

    def form_valid(self, form):
        # Generar número automático
        numero = generar_numero_acto(form.cleaned_data["tipo"])
        form.instance.numero = numero

        messages.success(self.request, f"Acto administrativo {numero} creado exitosamente.")
        return super().form_valid(form)


class ActoDetailView(LoginRequiredMixin, PermissionMixin, DetailView):
    """View administrative act details."""

    model = ActoAdministrativo
    template_name = "governance/acto_detail.html"
    context_object_name = "acto"
    pk_url_kwarg = "pk"


class ActoGeneratePdfView(JuntaPermissionMixin, View):
    """Generate PDF for an administrative act."""

    def get(self, request, pk):
        acto = get_object_or_404(ActoAdministrativo, uuid=pk)

        try:
            guardar_pdf_acto(acto)
            messages.success(request, "PDF generado exitosamente.")
        except ImportError as e:
            messages.error(request, f"WeasyPrint no está instalado: {e}")
        except Exception as e:
            messages.error(request, f"Error al generar PDF: {e}")

        return redirect("governance:acto_detail", pk=pk)


class ActoPublishView(JuntaPermissionMixin, View):
    """Publish an administrative act."""

    def post(self, request, pk):
        acto = get_object_or_404(ActoAdministrativo, uuid=pk)

        if acto.estado != ActoAdministrativo.Estado.FIRMADO:
            messages.error(request, "Solo se pueden publicar actos firmados.")
            return redirect("governance:acto_detail", pk=pk)

        acto.estado = ActoAdministrativo.Estado.PUBLICADO
        acto.fecha_publicacion = timezone.now()
        acto.save()

        messages.success(request, "Acto administrativo publicado exitosamente.")
        return redirect("governance:acto_detail", pk=pk)


# ============================================================================
# Listado Definitivo Views
# ============================================================================


class ListadoDefinitivoCreateView(JuntaPermissionMixin, TemplateView):
    """Create listing of definitive results."""

    template_name = "governance/listado_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["convocatorias"] = Convocatory.objects.filter(
            estado=Convocatory.Estado.DEFINITIVA
        )
        return context

    def post(self, request):
        convocatoria_id = request.POST.get("convocatoria")
        convocatoria = get_object_or_404(Convocatory, pk=convocatoria_id)

        # Obtener ranking final
        ranking_data = obtener_ranking_final(convocatoria)

        # Crear acto administrativo (borrador)
        numero = generar_numero_acto("resolucion")
        acto = ActoAdministrativo.objects.create(
            numero=numero,
            tipo=ActoAdministrativo.Tipo.RESOLUCION,
            fecha_expedicion=timezone.now().date(),
            asunto=f"Listado definitivo de beneficiarios - {convocatoria.nombre}",
            considerandos=[
                {"numeral": "1", "texto": "Que mediante convocatoria se establecieron los criterios de selección..."},
                {"numeral": "2", "texto": "Que agotado el proceso de reclamaciones y apelaciones..."},
            ],
            resolutivo=f"Se APRUEBA el listado definitivo de {len(ranking_data)} beneficiarios...",
            convocatoria=convocatoria,
            estado=ActoAdministrativo.Estado.BORRADOR,
        )

        # Crear listado definitivo
        listado = generar_listado_definitivo(convocatoria, acto, ranking_data)

        messages.success(request, f"Listado definitivo generado con {len(ranking_data)} beneficiarios.")
        return redirect("governance:listado_detail", pk=listado.uuid)


class ListadoDefinitivoDetailView(LoginRequiredMixin, PermissionMixin, DetailView):
    """View definitive listing details."""

    model = ListadoDefinitivo
    template_name = "governance/listado_detail.html"
    context_object_name = "listado"
    pk_url_kwarg = "pk"


class ListadoPublicoView(TemplateView):
    """Public view for definitive listings (portal de transparencia)."""

    template_name = "governance/listado_publico.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Obtener listados publicados
        listados = ListadoDefinitivo.objects.filter(
            acto__estado=ActoAdministrativo.Estado.PUBLICADO
        ).select_related("convocatoria", "acto")

        # Preparar datos para显示 (sin PII)
        listings = []
        for lst in listados:
            # Obtener información de beneficiarios (solo datos públicos)
            beneficiaries = []
            for item in lst.ranking[:10]:  # Solo top 10 para vista pública
                beneficiaries.append({
                    "rank": item["rank"],
                    "radicado": item["radicado"],
                    # No mostrar nombre - solo posición en ranking
                })

            listings.append({
                "uuid": str(lst.uuid),
                "convocatoria": lst.convocatoria.nombre,
                "fecha_publicacion": lst.fecha_publicacion,
                "acto_numero": lst.acto.numero,
                "total_beneficiarios": len(lst.ranking),
                "top_beneficiaries": beneficiaries,
            })

        context["listados"] = listings
        return context
