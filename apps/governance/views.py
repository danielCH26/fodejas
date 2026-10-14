"""HTML views for governance app (CHG-207 + CHG-208)."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.generic import (
    CreateView,
    DetailView,
    FormView,
    ListView,
    TemplateView,
)

from apps.accounts.permissions_mixin import JuntaPermissionMixin, PermissionMixin
from apps.convocatories.models import Convocatory
from apps.governance.domain.transitions import crear_modificatorio, firmar_acto
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
    fields = [
        "tipo",
        "fecha_expedicion",
        "asunto",
        "considerandos",
        "resolutivo",
        "convocatoria",
        "firmantes",
    ]
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


class ActoSignView(JuntaPermissionMixin, View):
    """Transition BORRADOR → FIRMADO (CHG-208).

    Receives the firmantes in the POST body as a single comma-separated
    field (``firmantes_csv``). Splits, strips, and passes them to
    ``apps.governance.domain.transitions.firmar_acto``.
    """

    def post(self, request, pk):
        csv = request.POST.get("firmantes_csv", "")
        firmantes = [s.strip() for s in csv.split(",") if s.strip()]
        if not firmantes:
            messages.error(
                request,
                "Debe indicar al menos un firmante (separados por coma).",
            )
            return redirect("governance:acto_detail", pk=pk)
        try:
            acto = firmar_acto(pk, firmantes, usuario=request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("governance:acto_detail", pk=pk)
        messages.success(
            request,
            f"Acto {acto.numero} firmado por {len(firmantes)} firmante(s).",
        )
        return redirect("governance:acto_detail", pk=acto.uuid)


class ActoModificatorioCreateView(JuntaPermissionMixin, FormView):
    """Create a CPACA Art. 45 acto modificatorio (CHG-208).

    GET renders the form pre-poblado con el acto original.
    POST crea el nuevo acto via
    ``apps.governance.domain.transitions.crear_modificatorio``.
    """

    template_name = "governance/acto_modificatorio_create.html"

    def dispatch(self, request, *args, **kwargs):
        self.original = get_object_or_404(ActoAdministrativo, uuid=kwargs.get("pk"))
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["original"] = self.original
        return ctx

    def post(self, request, *args, **kwargs):
        asunto = request.POST.get("asunto", "").strip()
        resolutivo = request.POST.get("resolutivo", "").strip()
        considerandos_raw = request.POST.get("considerandos", "[]").strip() or "[]"
        fecha_str = request.POST.get("fecha_expedicion", "").strip()

        if not asunto or not resolutivo:
            messages.error(request, "Asunto y resolutivo son obligatorios.")
            return redirect("governance:acto_modificatorio_create", pk=self.original.uuid)

        try:
            import json

            considerandos = json.loads(considerandos_raw)
            if not isinstance(considerandos, list):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            messages.error(request, "Considerandos debe ser JSON válido (lista).")
            return redirect("governance:acto_modificatorio_create", pk=self.original.uuid)

        fecha_expedicion = None
        if fecha_str:
            try:
                from datetime import date

                fecha_expedicion = date.fromisoformat(fecha_str)
            except ValueError:
                messages.error(
                    request,
                    "fecha_expedicion debe estar en formato AAAA-MM-DD.",
                )
                return redirect("governance:acto_modificatorio_create", pk=self.original.uuid)

        try:
            modificatorio = crear_modificatorio(
                self.original.uuid,
                asunto=asunto,
                considerandos=considerandos,
                resolutivo=resolutivo,
                fecha_expedicion=fecha_expedicion,
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("governance:acto_modificatorio_create", pk=self.original.uuid)

        messages.success(
            request,
            f"Acto modificatorio {modificatorio.numero} creado en BORRADOR.",
        )
        return redirect("governance:acto_detail", pk=modificatorio.uuid)


# ============================================================================
# Listado Definitivo Views
# ============================================================================


class ListadoDefinitivoCreateView(JuntaPermissionMixin, TemplateView):
    """Create listing of definitive results."""

    template_name = "governance/listado_create.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["convocatorias"] = Convocatory.objects.filter(estado=Convocatory.Estado.DEFINITIVA)
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
                {
                    "numeral": "1",
                    "texto": "Que mediante convocatoria se establecieron los criterios de selección...",
                },
                {
                    "numeral": "2",
                    "texto": "Que agotado el proceso de reclamaciones y apelaciones...",
                },
            ],
            resolutivo=f"Se APRUEBA el listado definitivo de {len(ranking_data)} beneficiarios...",
            convocatoria=convocatoria,
            estado=ActoAdministrativo.Estado.BORRADOR,
        )

        # Crear listado definitivo
        listado = generar_listado_definitivo(convocatoria, acto, ranking_data)

        messages.success(
            request, f"Listado definitivo generado con {len(ranking_data)} beneficiarios."
        )
        return redirect("governance:listado_detail", pk=listado.uuid)


class ListadoDefinitivoDetailView(LoginRequiredMixin, PermissionMixin, DetailView):
    """View definitive listing details."""

    model = ListadoDefinitivo
    template_name = "governance/listado_detail.html"
    context_object_name = "listado"
    pk_url_kwarg = "uuid"


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
                beneficiaries.append(
                    {
                        "rank": item["rank"],
                        "radicado": item["radicado"],
                        # No mostrar nombre - solo posición en ranking
                    }
                )

            listings.append(
                {
                    "uuid": str(lst.uuid),
                    "convocatoria": lst.convocatoria.nombre,
                    "fecha_publicacion": lst.fecha_publicacion,
                    "acto_numero": lst.acto.numero,
                    "total_beneficiarios": len(lst.ranking),
                    "top_beneficiaries": beneficiaries,
                }
            )

        context["listados"] = listings
        return context
