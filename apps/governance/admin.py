"""Admin configuration for governance app (CHG-207)."""
from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import ActoAdministrativo, ListadoDefinitivo, SecuencialActo


@admin.register(SecuencialActo)
class SecuencialActoAdmin(admin.ModelAdmin):
    """Admin for secuencial acts."""

    list_display = ["tipo", "anio", "secuencia"]
    list_filter = ["tipo", "anio"]
    search_fields = ["tipo"]
    ordering = ["-anio", "tipo"]


@admin.register(ActoAdministrativo)
class ActoAdministrativoAdmin(admin.ModelAdmin):
    """Admin for administrative acts."""

    list_display = [
        "numero",
        "tipo",
        "estado_badge",
        "convocatoria",
        "fecha_expedicion",
        "fecha_publicacion",
    ]
    list_filter = ["tipo", "estado", "fecha_expedicion"]
    search_fields = ["numero", "asunto", "convocatoria__nombre"]
    ordering = ["-created_at"]
    readonly_fields = ["uuid", "created_at", "updated_at", "pdf_sha256"]

    fieldsets = (
        (_("Información Principal"), {
            "fields": ("numero", "tipo", "convocatoria", "fecha_expedicion")
        }),
        (_("Contenido"), {
            "fields": ("asunto", "considerandos", "resolutivo")
        }),
        (_("Estado y Fechas"), {
            "fields": ("estado", "fecha_publicacion", "acto_original")
        }),
        (_("Archivo"), {
            "fields": ("pdf", "pdf_sha256")
        }),
        (_("Firmantes"), {
            "fields": ("firmantes",)
        }),
        (_("Metadata"), {
            "fields": ("uuid", "created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )

    def estado_badge(self, obj):
        """Display colored badge for estado."""
        colors = {
            "borrador": "#6c757d",
            "firmado": "#0d6efd",
            "publicado": "#198754",
            "anulado": "#dc3545",
        }
        color = colors.get(obj.estado, "#6c757d")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px;">{}</span>',
            color,
            obj.get_estado_display(),
        )
    estado_badge.short_description = _("Estado")


@admin.register(ListadoDefinitivo)
class ListadoDefinitivoAdmin(admin.ModelAdmin):
    """Admin for definitive listings."""

    list_display = [
        "uuid_short",
        "convocatoria",
        "acto",
        "fecha_publicacion",
        "total_beneficiarios",
    ]
    list_filter = ["fecha_publicacion"]
    search_fields = ["convocatoria__nombre", "acto__numero"]
    readonly_fields = ["uuid", "created_at", "fecha_publicacion"]

    def uuid_short(self, obj):
        """Display short UUID."""
        return str(obj.uuid)[:8]
    uuid_short.short_description = "UUID"

    def total_beneficiarios(self, obj):
        """Display total beneficiaries count."""
        return len(obj.ranking) if obj.ranking else 0
    total_beneficiarios.short_description = _("Beneficiarios")
