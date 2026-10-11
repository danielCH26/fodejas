# CHG-502 — Conflictos de Interés (CAP-018)

## Contexto

CAP-018 (Conflictos de Interés) es P1 en `project.md §8` y completa el
flujo de sesiones de CHG-501: hoy `MiembroSesion.conflicto_declarado` es
un flag manual sin proceso formal. La regla de negocio (project.md
§6.1.1, Ley 1952/2019): **el miembro declara el conflicto, la mayoría
simple de los demás presentes aprueba el impedimento, y su voto no se
cuenta para ese punto**.

## Capacidades afectadas

- CAP-018 — Conflictos de Interés
- CAP-017 — integración con sesiones (exclusión de voto por punto)

## Reglas de negocio afectadas

- project.md §6.1.1 — conflicto de intereses (Ley 1952/2019):
  declaración, aprobación del impedimento por mayoría simple, voto
  excluido para ese punto.
- CHG-501 — `registrar_voto` ya rechaza `conflicto_declarado` a nivel
  sesión; este change agrega la declaración formal **por punto**.

## Cambios propuestos

1. **Modelos** (`apps/governance/sessions/models.py`):
   - `DeclaracionConflicto`: FK `MiembroSesion` (declarante), FK
     `OrdenDelDiaPunto`, texto de la declaración, estado
     (PENDIENTE/APROBADA/RECHAZADA), revisado_por/revisado_at.
   - `VotoImpedimento`: FK declaracion, FK miembro_sesion (votante ≠
     declarante), a_favor bool, unique (declaracion, miembro).
2. **Servicios** (`sessions/services.py`):
   - `declarar_conflicto(sesion_id, punto_id, miembro_sesion_id,
     texto, actor)`: solo el propio miembro; solo puntos abiertos;
     deja la declaración PENDIENTE (bloquea su voto en ese punto).
   - `votar_impedimento(declaracion_id, miembro_sesion_id, a_favor,
     actor)`: votan los DEMÁS presentes con derecho a voto; tras cada
     voto se resuelve por mayoría simple de los presentes habilitados
     (mitad + 1): APROBADA → el voto del declarante queda excluido del
     punto (equivalente a conflicto efectivo); RECHAZADA → puede votar.
   - `registrar_voto`: rechaza voto si existe declaración PENDIENTE o
     APROBADA del miembro para ese punto.
   - Auditoría CAP-022 (declarar, votar impedimento, resolución).
3. **API** (SesionViewSet): `declarar_conflicto` (self) y
   `votar_impedimento` (otros miembros) actions + listado en el punto.
4. **Tests**: bloqueo de voto con declaración pendiente, aprobación por
   mayoría → voto excluido, rechazo del impedimento → puede votar,
   gating (solo el propio miembro declara; el declarante no vota el
   impedimento), auditoría.

## Criterios de aceptación

- [ ] Un miembro declara conflicto en un punto y su voto queda
      bloqueado hasta resolver el impedimento.
- [ ] El impedimento se aprueba por mayoría simple de los demás
      presentes; aprobado → el declarante no vota ese punto.
- [ ] Impedimento rechazado → el declarante puede votar.
- [ ] El declarante no vota su propio impedimento.
- [ ] Auditoría CAP-022 en declarar/votar/resolver.
- [ ] Suite completa verde en sqlite y PostgreSQL.

## Pruebas

- Unitarias: bloqueos, mayoría del impedimento, exclusión.
- Integración: API declarar/votar impedimento; flujo completo con
  exclusión.

## Riesgos y Fuera del alcance

- **Fuera del alcance**: registro permanente de impedimentos entre
  sesiones (historial institucional), reportes de COI (CHG-503).
- **Riesgo**: definición de "presentes habilitados" para la mayoría —
  se usa los presentes con derecho a voto excluyendo al declarante.
