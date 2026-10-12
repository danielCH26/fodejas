"""Serializers for Portal de Transparencia API (CHG-504, CAP-021).

All serializers expose ONLY aggregate/non-PII fields (project.md §14.2,
AGENTS.md §1, Ley 1581/2012). No field ever exposes nombre, documento,
email, firmantes, datos_academicos, or individual beneficiary data.
Field lists are explicit whitelists — no ModelSerializer with __all__.
"""

from rest_framework import serializers


class TransparenciaActoSerializer(serializers.Serializer):
    """Serializer for published actos (PUBLICADO only)."""

    numero = serializers.CharField(read_only=True)
    fecha_publicacion = serializers.CharField(read_only=True, allow_null=True)
    pdf_url = serializers.CharField(read_only=True, allow_null=True)
    convocatoria_nombre = serializers.CharField(read_only=True, allow_null=True)


class TransparenciaConvocatoriaSerializer(serializers.Serializer):
    """Serializer for open/closed convocatorias."""

    codigo = serializers.CharField(read_only=True)
    nombre = serializers.CharField(read_only=True)
    estado = serializers.CharField(read_only=True)
    fecha_apertura = serializers.CharField(read_only=True, allow_null=True)
    fecha_cierre = serializers.CharField(read_only=True, allow_null=True)


class TransparenciaEstadisticaSerializer(serializers.Serializer):
    """Serializer for aggregate statistics payload."""

    # Top-level sections (each is a list or dict from ReportingService)
    convocatorias = serializers.ListField(read_only=True)
    beneficiarios = serializers.ListField(read_only=True)
    ejecucion_presupuestal = serializers.DictField(read_only=True)
    seguimiento_academico = serializers.DictField(read_only=True)
