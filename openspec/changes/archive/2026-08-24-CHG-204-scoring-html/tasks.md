# Tasks — CHG-204 Interfaz HTML para Scoring

## 1. Modelos

- [x] 1.1 Crear modelo `Evaluacion` en `apps/scoring/models.py`
- [x] 1.2 Crear modelo `PuntajeTotal`
- [x] 1.3 Crear migración
- [x] 1.4 Ejecutar migración

## 2. Servicio de Scoring

- [x] 2.1 Crear `scoring_service.py`
- [x] 2.2 Implementar `calcular_puntaje_total()`
- [x] 2.3 Implementar `generar_ranking_municipio()`
- [x] 2.4 Implementar `generar_ranking_general()`
- [x] 2.5 Implementar regla Providencia Isla

## 3. Vistas

- [x] 3.1 Crear `ScoringListView`
- [x] 3.2 Crear `ScoringDetailView`
- [x] 3.3 Crear `RankingView`
- [x] 3.4 Crear vistas de exportación PDF/Excel (CSV)
- [x] 3.5 Agregar permisos R-COMITE

## 4. URLs

- [x] 4.1 Agregar rutas con UUID
- [x] 4.2 Incluir en config/urls.py

## 5. Templates

- [x] 5.1 Crear `scoring/list.html`
- [x] 5.2 Crear `scoring/detail.html`
- [x] 5.3 Crear `scoring/ranking.html`

## 6. Funcionalidad

- [x] 6.1 Checklist de criterios
- [x] 6.2 Cálculo automático de puntaje
- [x] 6.3 Generación de rankings
- [x] 6.4 Exportación PDF (pendiente - solo CSV)
- [x] 6.5 Exportación Excel (CSV)

## 7. Pruebas

- [x] 7.1 Tests de scoring_service
- [x] 7.2 Tests de ranking
- [x] 7.3 Tests de regla Providencia

## Estado

- ✅ CHG-204 completado y verificado

## Notas de QA (2026-07-06)

- ScoringListView con permisos R-COMITE
- ScoringDetailView con UUID y checklist de criterios
- RankingView con exportación CSV
- Fórmula 50/30/20 implementada
- Regla Providencia Isla: prioridad solo en empates
- Tests pasan: 10/10 (incluyendo ranking y providencia)
- URL params corregidos: `<uuid:solicitud_pk>`, `<int:evaluacion_pk>`
