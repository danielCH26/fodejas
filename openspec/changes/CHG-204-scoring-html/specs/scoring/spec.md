# Spec for CHG-204 — Interfaz HTML para Scoring

## Purpose

Interfaz HTML para que el Comité evaluador califique solicitudes verificadas y genere ranking (CAP-005).

## ADDED Requirements

### Requirement: Evaluacion Model

```
Evaluacion(
    solicitud FK,
    criterio_code str,  # e.g., "socioeconomico", "academico", "excelencia"
    puntaje Decimal(5,2),
    observaciones text,
    evaluado_por FK (User),
    created_at DateTime,
    updated_at DateTime
)
```

Uniqueness: `(solicitud, criterio_code)` — una evaluación por criterio.

### Requirement: PuntajeTotal Model

```
PuntajeTotal(
    solicitud FK,
    puntaje_socioeconomico Decimal(5,2),
    puntaje_academico Decimal(5,2),
    puntaje_excelencia Decimal(5,2),
    puntaje_total Decimal(5,2),
    ranking_municipio int NULL,
    ranking_general int NULL,
    observaciones text,
    calculado_por FK (User),
    fecha_calculo DateTime,
    created_at DateTime,
    updated_at DateTime
)
```

### Requirement: ScoringListView

- Filtro: solicitudes con `estado = verificada` (sin evaluación)
- Permiso: usuario con rol R-COMITE
- Columnas: radicado, aspirante, municipio, puntaje parcial

#### Scenario: Comité ve solicitudes pendientes

- GIVEN comité autenticado con rol R-COMITE
- WHEN visita `/scoring/`
- THEN ve lista de solicitudes verificadas pendientes de evaluación

### Requirement: ScoringDetailView

- Muestra los 3 grupos de criterios: socioeconómico (50%), académico (30%), excelencias (20%)
- Cada criterio tiene: nombre, descripción, campo puntaje (0-100), observaciones
- Puntaje total se calcula automáticamente

#### Scenario: Evaluar solicitud

- GIVEN evaluador en detalle de solicitud
- WHEN ingresa puntajes y guarda
- THEN `Evaluacion` se crea por cada criterio
- AND `PuntajeTotal` se calcula

### Requirement: Cálculo de Puntaje

La fórmula SHALL ser:
```
puntaje_total = (puntaje_socioeconomico * 0.50) +
                (puntaje_academico * 0.30) +
                (puntaje_excelencia * 0.20)
```

Los pesos son configurables en `ConfiguracionConvocatoria.criterios`.

#### Scenario: Cálculo automático

- GIVEN evaluaciones completadas para los 3 grupos
- WHEN se calcula puntaje total
- THEN se aplica fórmula con los pesos configurados

### Requirement: Ranking

Dos rankings SHALL generarse:

1. **Ranking por Municipio**: basado en puntaje_total dentro de cada municipio
2. **Ranking General**: basado en puntaje_total global

#### Scenario: Generación de ranking

- GIVEN todas las solicitudes evaluadas
- WHEN se genera ranking
- THEN `ranking_municipio` y `ranking_general` se calculan
- AND empates se resuelven por fecha de radicación

### Requirement: Regla Providencia Isla

Los solicitantes de Providencia Isla SHALL tener prioridad en caso de empate.

#### Scenario: Empaque con Providencia

- GIVEN solicitante A (Providencia) y B (San Andrés) empatados en puntaje
- WHEN se genera ranking
- THEN A aparece antes que B

### Requirement: RankingView

- Tabla con todas las solicitudes evaluadas
- Columnas: ranking, radicado, nombre, municipio, puntaje total
- Filtros: por municipio, por rango de puntaje
- Orden: por ranking_general

### Requirement: Exportación

- Botón "Exportar PDF" — ranking formal
- Botón "Exportar Excel" — datos para spreadsheet

### Requirement: Seguridad

- Solo R-COMITE puede acceder a vistas de scoring
- UUID en todas las URLs

## MODIFIED Files

- `apps/scoring/models.py` — agregar modelos
- `apps/scoring/views.py` — agregar vistas
- `apps/scoring/urls.py` — agregar URLs
- `templates/scoring/` — templates

## Acceptance Criteria

- [ ] Modelos Evaluacion y PuntajeTotal existen
- [ ] Lista de solicitudes verificadas visible para R-COMITE
- [ ] Formulario de evaluación con 3 grupos de criterios
- [ ] Cálculo automático de puntaje total con pesos 50/30/20
- [ ] Ranking por municipio generado
- [ ] Ranking general generado
- [ ] Regla Providencia Isla aplicada en empates
- [ ] Exportación PDF y Excel funciona
- [ ] Todas las URLs usan UUID
- [ ] Permisos correctamente aplicados
