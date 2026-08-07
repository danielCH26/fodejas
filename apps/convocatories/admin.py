"""Admin configuration for convocatories app."""
from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    ConfiguracionConvocatoria,
    ConvocatoriaVersion,
    Convocatory,
    Cupo,
    Hito,
)


class HitoInline(admin.TabularInline):
    """Inline admin for Hito (milestones)."""

    model = Hito
    extra = 0
    min_num = 0
    fields = ("codigo", "orden", "fecha_inicio", "fecha_fin", "responsable")
    ordering = ("orden",)


class CupoInline(admin.TabularInline):
    """Inline admin for Cupo (quotas)."""

    model = Cupo
    extra = 0
    min_num = 0
    fields = ("municipio", "modalidad", "nivel", "cantidad", "regla_especial")
    ordering = ("municipio", "modalidad", "nivel")


@admin.register(Convocatory)
class ConvocatoryAdmin(admin.ModelAdmin):
    """Admin for Convocatory."""

    list_display = (
        "codigo",
        "nombre",
        "tipo",
        "periodo",
        "estado",
        "created_at",
    )
    list_filter = ("estado", "tipo", "periodo")
    search_fields = ("codigo", "nombre")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "estado")

    fieldsets = (
        (_("Información básica"), {
            "fields": ("codigo", "nombre", "tipo", "periodo")
        }),
        (_("Fechas"), {
            "fields": (
                "fecha_publicacion",
                "fecha_apertura",
                "fecha_cierre",
                "fecha_publicacion_preliminar",
                "fecha_publicacion_definitiva",
            )
        }),
        (_("Configuración"), {
            "fields": (
                "modalidad_apoyo",
                "monto_semestre_smlmv",
                "duracion_maxima_semestres",
                "cupo_total",
            )
        }),
        (_("Estado"), {
            "fields": ("estado",),
            "description": "El estado se modifica mediante las acciones below",
        }),
        (_("Auditoría"), {
            "fields": ("created_by", "created_at", "updated_at"),
            "classes": ("collapse",),
        }),
    )

    actions = ["publicar_convocatoria", "cerrar_convocatoria", "cancelar_convocatoria"]

    def publicar_convocatoria(self, request, queryset):
        """Publish selected convocatorias."""
        from apps.convocatories.services import convocatoria_service

        for conv in queryset:
            try:
                convocatoria_service.publicar(conv, request.user)
            except Exception as e:
                self.message_user(request, f"Error en {conv.codigo}: {e}", level="error")

    publicar_convocatoria.short_description = "Publicar convocatorias"

    def cerrar_convocatoria(self, request, queryset):
        """Close selected convocatorias."""
        from apps.convocatories.services import convocatoria_service

        for conv in queryset:
            try:
                convocatoria_service.cerrar(conv, request.user)
            except Exception as e:
                self.message_user(request, f"Error en {conv.codigo}: {e}", level="error")

    cerrar_convocatoria.short_description = "Cerrar convocatorias"

    def cancelar_convocatoria(self, request, queryset):
        """Cancel selected convocatoria with a default reason."""
        from apps.convocatories.services import convocatoria_service

        for conv in queryset:
            try:
                motivo = request.POST.get("motivo", "Cancelada por administrador")
                convocatoria_service.cancelar(conv, request.user, motivo)
            except Exception as e:
                self.message_user(request, f"Error en {conv.codigo}: {e}", level="error")

    cancelar_convocatoria.short_description = "Cancelar convocatorias"


@admin.register(ConfiguracionConvocatoria)
class ConfiguracionConvocatoriaAdmin(admin.ModelAdmin):
    """Admin for ConfiguracionConvocatoria with inline Hitos and Cupos."""

    list_display = (
        "__str__",
        "convocatoria",
        "schema_version",
        "created_at",
    )
    list_filter = ("schema_version",)
    search_fields = ("convocatoria__codigo",)
    readonly_fields = ("created_at",)

    inlines = [HitoInline, CupoInline]

    fieldsets = (
        (_("Configuración"), {
            "fields": ("convocatoria", "schema_version", "descripcion")
        }),
        (_("Payload (JSON)"), {
            "fields": ("payload",),
            "classes": ("collapse",),
        }),
        (_("Auditoría"), {
            "fields": ("created_by", "created_at", "valida_hasta"),
            "classes": ("collapse",),
        }),
    )


@admin.register(Hito)
class HitoAdmin(admin.ModelAdmin):
    """Admin for Hito."""

    list_display = ("codigo", "config", "orden", "responsable", "fecha_inicio", "fecha_fin")
    list_filter = ("config__convocatoria",)
    search_fields = ("codigo", "config__convocatoria__codigo")
    ordering = ("config", "orden")


@admin.register(Cupo)
class CupoAdmin(admin.ModelAdmin):
    """Admin for Cupo."""

    list_display = ("__str__", "config", "municipio", "modalidad", "nivel", "cantidad")
    list_filter = ("config__convocatoria", "municipio", "modalidad", "nivel")
    search_fields = ("config__convocatoria__codigo",)
    ordering = ("config", "municipio", "modalidad", "nivel")


@admin.register(ConvocatoriaVersion)
class ConvocatoriaVersionAdmin(admin.ModelAdmin):
    """Admin for ConvocatoriaVersion (read-only history)."""

    list_display = (
        "__str__",
        "convocatoria",
        "version",
        "created_by",
        "created_at",
    )
    list_filter = ("convocatoria",)
    ordering = ("convocatoria", "-version")
    readonly_fields = (
        "convocatoria",
        "version",
        "schema_version",
        "snapshot",
        "created_by",
        "created_at",
        "valida_hasta",
    )

    def has_add_permission(self, request):
        """Prevent manual creation of versions."""
        return False

    def has_change_permission(self, request, obj=None):
        """Versions are immutable."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent deletion of version history."""
        return False
