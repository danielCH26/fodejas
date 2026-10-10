"""Admin configuration for claims app."""

from django.contrib import admin

from apps.claims.models import Apelacion, ApelacionHistorial, Reclamacion, ReclamacionHistorial


@admin.register(Reclamacion)
class ReclamacionAdmin(admin.ModelAdmin):
    """Admin for Reclamacion model."""

    list_display = ["uuid", "solicitud", "tipo", "estado", "created_at"]
    list_filter = ["estado", "tipo", "created_at"]
    search_fields = ["uuid", "solicitud__radicado", "descripcion"]
    readonly_fields = ["uuid", "created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        (
            "Información Basic",
            {"fields": ("uuid", "solicitud", "tipo", "descripcion", "evidencia")},
        ),
        ("Estado", {"fields": ("estado", "respuesta", "resuelto_por", "fecha_resolucion")}),
        ("Metadatos", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(ReclamacionHistorial)
class ReclamacionHistorialAdmin(admin.ModelAdmin):
    """Admin for ReclamacionHistorial model."""

    list_display = ["reclamacion", "estado_anterior", "estado_nuevo", "actor", "created_at"]
    list_filter = ["estado_nuevo", "created_at"]
    search_fields = ["reclamacion__uuid", "observacion"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]


@admin.register(Apelacion)
class ApelacionAdmin(admin.ModelAdmin):
    """Admin for Apelacion model."""

    list_display = ["uuid", "reclamacion", "estado", "created_at", "fecha_resolucion"]
    list_filter = ["estado", "created_at", "fecha_resolucion"]
    search_fields = ["uuid", "reclamacion__uuid", "descripcion"]
    readonly_fields = ["uuid", "created_at", "updated_at"]
    ordering = ["-created_at"]

    fieldsets = (
        ("Información Basic", {"fields": ("uuid", "reclamacion", "descripcion", "evidencia")}),
        ("Estado", {"fields": ("estado", "respuesta", "resuelto_por", "fecha_resolucion")}),
        ("Metadatos", {"fields": ("created_at", "updated_at"), "classes": ("collapse",)}),
    )


@admin.register(ApelacionHistorial)
class ApelacionHistorialAdmin(admin.ModelAdmin):
    """Admin for ApelacionHistorial model."""

    list_display = ["apelacion", "estado_anterior", "estado_nuevo", "actor", "created_at"]
    list_filter = ["estado_nuevo", "created_at"]
    search_fields = ["apelacion__uuid", "observacion"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]
