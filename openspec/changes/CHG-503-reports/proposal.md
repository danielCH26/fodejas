# CHG-503 — Reportes de Gestión (CAP-020)

## Contexto

CAP-020 (Reportes de Gestión trimestrales y anuales) es **P0** en
`project.md §8` y su entregable es el segundo ítem de Fase 5
(`roadmap.md §9.2`: "Se generan los informes trimestrales y anuales con
KPIs normativos"). La app `apps/reporting/` fue removida como stub en
CHG-806 y no existía implementación previa.

Requisitos de `project.md §14.1` (informes internos para R-COORD,
R-JUNTA, R-SECEDU):

- Ejecución presupuestal (mensual / trimestral).
- Beneficiarios por cohorte / convocatoria (agregados, no nominales).
- Estado de seguimiento académico (al día / en riesgo / suspendido /
  graduado).
- Pagos pendientes, en proceso y pagados.
- Tasa de graduación.

**Fuera del alcance de este change**: portal público (CHG-504, §14.2),
exportación a entes de control (CHG-505, §14.3), estudio de impacto
(CHG-506).

## Capacidades afectadas

- CAP-020 — Reportes de Gestión

## Reglas de negocio afectadas

- project.md §14.1 — contenidos de los informes internos
- project.md §14 general — agregados sin datos personales (PII)
- AGENTS.md §1 — sin datos personales en reportes

## Cambios propuestos

1. **App** `apps/reporting/` recreada (sin modelos: reportes calculados
   on-demand sobre los datos transaccionales).
2. **Servicio** `ReportingService` con agregaciones:
   - `resumen_convocatorias()`: postulaciones por convocatoria con
     desglose por estado (Solicitud).
   - `beneficiarios_por_convocatoria()`: procesos de legalización por
     convocatoria y estado (CAP-009).
   - `ejecucion_presupuestal(desde, hasta)`: montos ordenados / pagados
     / pendientes de desembolsos (CAP-010) en el periodo.
   - `seguimiento_academico()`: expedientes por estado (CAP-011) y
     tasa de graduación.
   - `informe_periodo(anio, trimestre|None)`: compone el informe
     trimestral o anual con los KPIs anteriores.
3. **API** (read-only): `/api/reporting/gestion/` con gating
   `HasAnyRole(['R-COORD', 'R-JUNTA', 'R-ADMIN'])` — sin PII (solo
   agregados y montos).
4. **Tests**: agregaciones con datos sintéticos, filtro de periodo,
   gating por rol, ausencia de PII en la respuesta.

## Criterios de aceptación

- [ ] El informe trimestral/anual compone los KPIs de §14.1.
- [ ] Las agregaciones son correctas contra datos sintéticos conocidos.
- [ ] Solo R-COORD/R-JUNTA/R-ADMIN acceden; otros roles → 403.
- [ ] La respuesta no contiene emails, nombres ni documentos.
- [ ] Suite completa verde en sqlite y PostgreSQL.

## Pruebas

- Unitarias del servicio (cada KPI con datos sembrados conocidos).
- API: gating, periodo inválido, sin PII.
- Suite completa ambos motores.

## Riesgos y Fuera del alcance

- **Fuera del alcance**: CHG-504/505/506, exportación sellada,
  configuración de umbrales por convocatoria.
- **Riesgo**: agregaciones por IES/municipio dependen de campos JSON de
  Solicitud (datos_academicos) — se diferida a CHG-504/506 donde el
  portal las requiera; este change reporta por convocatoria/estado.
