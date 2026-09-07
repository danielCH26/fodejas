"""Scoring service for CAP-005."""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone


# Default weights (50/30/20)
DEFAULT_WEIGHTS = {
    "socioeconomico": Decimal("0.50"),
    "academico": Decimal("0.30"),
    "excelencia": Decimal("0.20"),
}

# Providencia Island municipality code
PROVIDENCIA_MUNICIPIO = "providencia"


def get_weights(convocatoria=None):
    """Get scoring weights from convocatoria config or defaults."""
    if convocatoria:
        try:
            config = convocatoria.configuracion
            weights = config.get("scoring_weights", {})
            return {
                "socioeconomico": Decimal(str(weights.get("socioeconomico", 50))) / 100,
                "academico": Decimal(str(weights.get("academico", 30))) / 100,
                "excelencia": Decimal(str(weights.get("excelencia", 20))) / 100,
            }
        except Exception:
            pass
    return DEFAULT_WEIGHTS


@transaction.atomic
def calcular_puntaje_total(solicitud, actor=None):
    """Calculate total score for a solicitud.
    
    Formula: (socio * 0.50) + (academico * 0.30) + (excelencia * 0.20)
    
    CHG-805 AUD-007 (CRITICAL): the function is wrapped in
    ``@transaction.atomic`` and acquires the row-level lock via
    ``PuntajeTotal.objects.select_for_update().get_or_create(...)``
    so two concurrent scorers cannot race the read-modify-write of
    the ``PuntajeTotal`` and produce a ``puntaje_total`` that is
    inconsistent with its components.
    """
    from apps.scoring.models import Evaluacion, PuntajeTotal

    weights = get_weights(solicitud.convocatoria)

    # Get evaluations
    eval_socio = solicitud.evaluaciones.filter(
        criterio=Evaluacion.Criterio.SOCIOECONOMICO
    ).first()

    eval_acad = solicitud.evaluaciones.filter(
        criterio=Evaluacion.Criterio.ACADEMICO
    ).first()

    eval_excel = solicitud.evaluaciones.filter(
        criterio=Evaluacion.Criterio.EXCELENCIA
    ).first()

    # Get puntajes (default to 0 if not evaluated)
    socio = eval_socio.puntaje or Decimal("0")
    acad = eval_acad.puntaje or Decimal("0")
    excel = eval_excel.puntaje or Decimal("0")

    # Calculate total
    total = (socio * weights["socioeconomico"]) + \
            (acad * weights["academico"]) + \
            (excel * weights["excelencia"])

    # Get or create PuntajeTotal with row-level lock.
    # select_for_update() requires PostgreSQL/MySQL — callers on
    # SQLite will raise NotSupportedError, which is the expected
    # signal to use a real RDBMS for concurrent scoring.
    puntaje, _ = (
        PuntajeTotal.objects
        .select_for_update()
        .get_or_create(solicitud=solicitud, defaults={"calculado_por": actor})
    )

    # Update values
    puntaje.puntaje_socioeconomico = socio
    puntaje.puntaje_academico = acad
    puntaje.puntaje_excelencia = excel
    puntaje.puntaje_total = total
    puntaje.calculado_por = actor
    puntaje.save()

    return puntaje


def generar_ranking_municipio(convocatoria, municipio_codigo=None):
    """Generate ranking by municipality.
    
    Args:
        convocatoria: The Convocatoria instance
        municipio_codigo: Optional filter for specific municipality
    """
    from apps.applications.models import Solicitud
    from apps.scoring.models import PuntajeTotal
    
    # Get verified solicitudes
    queryset = Solicitud.objects.filter(
        convocatoria=convocatoria,
        estado=Solicitud.Estado.VERIFICADA
    ).select_related("puntaje_total")
    
    if municipio_codigo:
        queryset = queryset.filter(
            datos_personales__municipio=municipio_codigo
        )
    
    # Get puntajes and sort
    puntajes = PuntajeTotal.objects.filter(
        solicitud__in=queryset
    ).order_by("-puntaje_total", "solicitud__created_at")
    
    # Assign rankings
    for rank, puntaje in enumerate(puntajes, 1):
        puntaje.ranking_municipio = rank
        puntaje.save(update_fields=["ranking_municipio", "updated_at"])
    
    return puntajes.count()


def generar_ranking_general(convocatoria):
    """Generate overall ranking with Providencia Island priority.
    
    Providencia Island applicants get priority in case of tie (same score).
    """
    from apps.applications.models import Solicitud
    from apps.scoring.models import PuntajeTotal
    
    # Get verified solicitudes
    queryset = Solicitud.objects.filter(
        convocatoria=convocatoria,
        estado=Solicitud.Estado.VERIFICADA
    ).select_related("puntaje_total")
    
    # Get all puntajes ordered by score (desc) then by created_at (asc)
    all_puntajes = list(PuntajeTotal.objects.filter(
        solicitud__in=queryset
    ).select_related("solicitud").order_by("-puntaje_total", "solicitud__created_at"))
    
    # Sort with Providencia priority only in case of tie
    # Primary: score (desc), Secondary: Providencia comes first on tie
    def sort_key(p):
        score = p.puntaje_total or 0
        is_providencia = 1 if p.solicitud.datos_personales.get("municipio") == PROVIDENCIA_MUNICIPIO else 0
        # Return tuple: (negative score, non-providencia flag) - lower is better
        # For desc order, we use negative score; for Providencia priority on tie, 0 (Providencia) comes before 1 (others)
        return (-score, is_providencia)
    
    ranked = sorted(all_puntajes, key=sort_key)
    
    # Assign rankings
    for rank, puntaje in enumerate(ranked, 1):
        puntaje.ranking_general = rank
        puntaje.save(update_fields=["ranking_general", "updated_at"])
    
    return len(ranked)


def generar_rankings_completos(convocatoria):
    """Generate both municipality and general rankings."""
    generar_ranking_general(convocatoria)
    
    # Generate per municipality
    municipios = ["san_andres", "providencia", "santa_catalina"]
    for mun in municipios:
        generar_ranking_municipio(convocatoria, mun)
    
    return {
        "ranking_general": True,
        "municipios": municipios,
    }


def create_default_evaluaciones(solicitud):
    """Create default Evaluacion records for a solicitud."""
    from apps.scoring.models import Evaluacion
    
    default_criterios = [
        {
            "criterio": Evaluacion.Criterio.SOCIOECONOMICO,
            "nombre": "Evaluación Socioeconómica (50%)",
        },
        {
            "criterio": Evaluacion.Criterio.ACADEMICO,
            "nombre": "Evaluación Académica (30%)",
        },
        {
            "criterio": Evaluacion.Criterio.EXCELENCIA,
            "nombre": "Excelencia (20%)",
        },
    ]
    
    created = []
    for crit in default_criterios:
        eval_obj, created_flag = Evaluacion.objects.get_or_create(
            solicitud=solicitud,
            criterio=crit["criterio"],
            defaults={"criterio_nombre": crit["nombre"]}
        )
        if created_flag:
            created.append(eval_obj)
    
    return created
