# CHG-501 — Sesiones de Junta y Comité Técnico (CAP-017)

## Contexto

CAP-017 (Sesiones de Junta y Comité Técnico: actas, votaciones) es P0
en `project.md §8` y su entregable es el primer ítem de Fase 5
(`roadmap.md §9.2`). Hoy `apps/governance/sessions/` es un placeholder
(CHG-806) y las decisiones de la Junta se documentan solo como actos
administrativos sueltos: no existe trazabilidad de **quién sesionó,
con qué quórum, qué se votó y cómo quedó el acta**.

Reglas de negocio aplicables (proyecto.md §6.1.1-6.1.2):

- **Quórum**: mayoría simple (mitad + 1). Decisiones por mayoría simple.
- **Sesiones**: mínimo 2 ordinarias/año; convocatoria escrita 5 días
  hábiles (ordinaria) o 2 días hábiles (extraordinaria). Presenciales
  o virtuales. **Actas firmadas**.
- **Comité Técnico** (Art. 6 Decreto 0372/2025): mínimo 5 miembros,
  sin superposición con la Junta, sesiona trimestralmente; sus
  recomendaciones NO son vinculantes.
- **Excepción por cargo**: Gobernador, Alcalde y Secretario no votan.

## Capacidades afectadas

- CAP-017 — Sesiones de Junta y Comité Técnico (actas, votaciones)

## Reglas de negocio afectadas

- project.md §6.1.1 — quórum, convocatoria, actas firmadas,
  excepción por cargo
- project.md §6.1.2 — Comité Técnico (mínimo 5, no vinculante)
- AGENTS.md §7 — actas con firma electrónica (CAP-029) y auditoría
  (CAP-022)

## Cambios propuestos

1. **Modelos** (`apps/governance/sessions/models.py`):
   - `Sesion`: tipo (ORDINARIA/EXTRAORDINARIA), órgano (JUNTA/CT),
     fecha/hora, convocatoria_enviada_at, estado
     (CONVOCADA/EN_SESION/FINALIZADA/ANULADA), quórum calculado.
   - `MiembroSesion`: asistencia por miembro (presente/virtual/ausente),
     rol, exención de voto por cargo (Gobernador/Alcalde/Secretario).
   - `OrdenDelDiaPunto`: puntos numerados, texto, resultado de votación.
   - `Voto`: voto por miembro y punto (A_FAVOR/EN_CONTRA/ABSTENCION),
     excluyendo miembros con conflicto declarado (CAP-018 vía flag;
     la declaración formal es CHG-502).
   - `ActaSesion`: acta generada (HTML/PDF vía CAP-029) con hash
     SHA-256, firmantes y estado de firma.
2. **Servicios** (`apps/governance/sessions/services.py`):
   - `convocar_sesion` (valida anticipos 5/2 días hábiles).
   - `registrar_asistencia` + `calcular_quorum` (mitad + 1 de los
     miembros con voto).
   - `abrir_sesion` (exige quórum), `agregar_punto`, `registrar_voto`
     (rechaza exentos por cargo y conflictos declarados),
     `cerrar_punto` (mayoría simple), `finalizar_sesion`,
     `generar_acta` (reutiliza el patrón PDF + SHA-256 de
     governance/services/pdf.py) y `firmar_acta` (CAP-029).
   - Auditoría CAP-022 en cada transición (fail-closed, sin
     try/except).
3. **API/Views** (`apps/governance/sessions/views.py` + urls):
   - ViewSets DRF con matriz de roles: convocatoria/gestión →
     `R-JUNTA` (presidencia) y `R-ADMIN`; asistencia/votación →
     miembros de la sesión; consulta de actas → `R-JUNTA`, `R-ADMIN`,
     `R-CT`, `R-OFIJUR`.
   - Ownership: cada miembro vota solo por sí mismo.
4. **Tests**: quórum (mitad+1, exentos por cargo no cuentan para el
   quórum de votación), anticipos de convocatoria (5/2 días hábiles),
   suspensión automática por falta de quórum, voto excluido por
   conflicto, mayoría simple, acta con hash, auditoría, API gating.
5. **Seed**: los miembros de Junta/CT se gestionan por roles existentes
   (R-JUNTA, R-PRES, R-SECEDU, R-CT); no se crean roles nuevos.

## Criterios de aceptación

- [ ] Una sesión ordinaria requiere convocatoria con ≥5 días hábiles de
      anticipación; una extraordinaria ≥2 (validado en servicio).
- [ ] La sesión no puede abrirse sin quórum (mitad + 1 de miembros con
      derecho a voto).
- [ ] Los miembros por cargo (Gobernador/Alcalde/Secretario) no votan.
- [ ] Cada punto se aprueba por mayoría simple de los votos emitidos.
- [ ] El acta se genera con hash SHA-256 y queda firmada electrónicamente
      (CAP-029) antes de archivarse.
- [ ] Toda transición deja evento de auditoría (CAP-022).
- [ ] Suite completa verde en sqlite y PostgreSQL; CI Test job verde.

## Pruebas

- Unitarias: quórum, anticipos, mayoría simple, exclusión por
  cargo/conflicto, hash del acta.
- Integración: flujo completo convocar→asistencia→abrir→votar→
  finalizar→acta→firma; gating de API por rol.
- Regresión: suite completa en ambos motores (sqlite/PostgreSQL).

## Riesgos y Fuera del alcance

- **Fuera del alcance**: declaración formal de conflicto de interés con
  aprobación del impedimento (CHG-502 — aquí solo el flag que excluye
  el voto), notificaciones (CAP-019), portal de transparencia (CAP-021),
  cobro coactivo.
- **Riesgo**: las reglas de quórum/votación provienen de project.md
  §6.1.1; si la Junta adopta un reglamento interno distinto, los
  umbrales deben volverse configurables (queda como upgrade, no bloquea).
- **Riesgo**: firmas del acta dependen de CAP-029 (ya implementado).
