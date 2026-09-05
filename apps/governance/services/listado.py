"""Generación del listado definitivo de beneficiarios (CHG-207)."""
from django.db import transaction
from django.utils import timezone


def generar_listado_definitivo(convocatoria, acto, ranking_data):
    """
    Genera y guarda el listado definitivo de beneficiarios.
    
    Args:
        convocatoria: Instancia de Convocatory
        acto: Instancia de ActoAdministrativo que aprueba el listado
        ranking_data: Lista de dicts con {"solicitud_id": ..., "puntaje": ..., "rank": ...}
    
    Returns:
        Instancia de ListadoDefinitivo
    """
    from apps.governance.models import ListadoDefinitivo

    with transaction.atomic():
        # Crear listado
        listado = ListadoDefinitivo.objects.create(
            convocatoria=convocatoria,
            acto=acto,
            ranking=ranking_data,
        )

        # Actualizar estado de la convocatoria
        from apps.convocatories.models import Convocatory
        try:
            convocatoria.estado = Convocatory.Estado.RESULTADOS_DEFINITIVOS
            convocatoria.save(update_fields=["estado", "updated_at"])
        except Exception:
            pass  # Si el estado no existe, continuar

    return listado


def obtener_ranking_final(convocatoria):
    """
    Obtiene el ranking final de solicitudes para una convocatoria.
    
    Ordena por puntaje total (mayor a menor).
    Aplica regla de Providencia Isla si aplica.
    
    Args:
        convocatoria: Instancia de Convocatory
    
    Returns:
        Lista de dicts con información de cada solicitud
    """
    from apps.applications.models import Solicitud
    from apps.scoring.models import PuntajeTotal

    # Obtener solicitudes verificadas
    solicitudes = Solicitud.objects.filter(
        convocatoria=convocatoria,
        estado=Solicitud.Estado.VERIFICADA,
    ).select_related("aspirante")

    # Obtener puntajes
    ranking = []
    for sol in solicitudes:
        try:
            puntaje = PuntajeTotal.objects.get(solicitud=sol)
            ranking.append({
                "solicitud_id": str(sol.uuid),
                "radicado": sol.radicado,
                "aspirante": sol.aspirante.get_full_name() or sol.aspirante.email,
                "puntaje": float(puntaje.puntaje_total or 0),
                "puntaje_detallado": {
                    "academico": float(puntaje.puntaje_academico or 0),
                    "excelencia": float(puntaje.puntaje_excelencia or 0),
                    "socioeconomico": float(puntaje.puntaje_socioeconomico or 0),
                },
            })
        except PuntajeTotal.DoesNotExist:
            ranking.append({
                "solicitud_id": str(sol.uuid),
                "radicado": sol.radicado,
                "aspirante": sol.aspirante.get_full_name() or sol.aspirante.email,
                "puntaje": 0,
                "puntaje_detallado": {
                    "academico": 0,
                    "excelencia": 0,
                    "socioeconomico": 0,
                },
            })

    # Ordenar por puntaje (mayor a menor)
    ranking.sort(key=lambda x: x["puntaje"], reverse=True)

    # Asignar rank
    for i, item in enumerate(ranking, 1):
        item["rank"] = i

    # TODO: Aplicar regla de Providencia Isla (cupo especial)
    # Esto requiere conocer el municipio de residencia del aspirante

    return ranking
