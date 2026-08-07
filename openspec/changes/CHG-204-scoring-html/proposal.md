# CHG-204 — Interfaz HTML para Scoring y Evaluaciones

## Contexto

CAP-005 define el motor de scoring configurable (50/30/20) + ranking por municipio + regla Providencia Isla. Se necesita interfaz HTML para que el Comité evaluador califique solicitudes verificadas y genere el ranking.

## Capacidades afectadas

- **CAP-005** — Motor de scoring configurable + ranking
- **CAP-008** — Resultados definitivos

## Reglas de negocio afectadas

- `project.md` §10.2 — Criterios 50/30/20 (50% socioeconómico, 30% académico, 20% excelencias)
- Regla de desempate por municipio
- Regla de excepción Providencia Isla (prioridad)

## Cambios propuestos

1. **Modelo de Evaluación**:
   - `Evaluacion(solicitud FK, criterio, puntaje, observaciones, evaluado_por, fecha)`
   - `PuntajeTotal(solicitud, total, ranking_municipio, ranking_general)`

2. **Vistas HTML** en `apps/scoring/views.py`:
   - `ScoringListView` — lista de solicitudes verificadas pendientes de evaluación
   - `ScoringDetailView` — evaluación por criterios
   - `RankingView` — ranking general y por municipio
   - `ScoringResultView` — resultados finales

3. **URLs con UUID**:
   - `/scoring/` — lista de evaluaciones
   - `/scoring/<uuid>/` — evaluar solicitud
   - `/scoring/<uuid>/ranking/` — ver ranking
   - `/scoring/resultados/` — resultados finales

4. **Motor de cálculo**:
   - Aplicar criterios 50/30/20
   - Generar ranking por municipio
   - Aplicar regla Providencia Isla

## Criterios de aceptación

- [ ] Lista de solicitudes verificadas lista para scoring
- [ ] Formulario de evaluación con criterios configurables
- [ ] Cálculo automático de puntaje total
- [ ] Ranking por municipio generado
- [ ] Regla Providencia Isla aplicada correctamente
- [ ] Ranking general visible
- [ ] Exportar a PDF/Excel
- [ ] Todas las URLs usan UUID

## Pruebas

- Tests del motor de scoring
- Tests de ranking
- Tests de regla Providencia Isla

## Outside Scope

- Reclamaciones (CHG-205)
- Apelaciones (CHG-206)
- Resultados definitivos (CAP-008, CHG-207)

## Notas

- Usar UUID en URLs
- Permisos: solo R-COMITE pueden evaluar
- Integración con notifications para notificar resultados
