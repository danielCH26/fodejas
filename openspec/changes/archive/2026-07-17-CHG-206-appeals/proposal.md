# Proposal: CHG-206 — Apelaciones (2ª instancia ante la Oficina Jurídica)

## Intent

CHG-205 implementó la **1ª instancia** (reclamaciones ante la Junta,
`project.md §10.3`). El aspirante insatisfecho debe poder **apelar
ante la Oficina Jurídica de la Gobernación** (CAP-007) en 2ª
instancia, quien emite **resolución definitiva**. Sin CHG-206 el
ciclo `Reclamación → Apelación → Resolución OJ` queda roto y se
compromete el debido proceso CPACA (`project.md §13.4`).

## Scope

### In Scope
- Modelos `Apelacion` (FK a `Reclamacion`) y `ApelacionHistorial`
  en `apps/claims/`.
- Vistas HTML para `R-ASPIRANTE` (presentar) y `R-OFIJUR`
  (gestionar).
- Rol `R-OFIJUR` vía data migration; transiciones, validaciones,
  migración, admin, tests.

### Out of Scope
- Notificaciones (CAP-019) — postergado; modelo `Notification` ya
  existe.
- Bitácora global inmutable (CAP-022) — historial local cubre lo
  básico.
- Apelaciones de sanciones (CAP-016, Art. 17 Decreto 0372/2025).
- Acto administrativo definitivo (CAP-008) — eso es CHG-207.

## Capabilities

### New Capabilities
- `apelaciones-2da-instancia` (CAP-007) — recurso administrativo en
  2ª instancia ante la Oficina Jurídica, en `apps/claims/`.

### Modified Capabilities
- None. CAP-006 (`openspec/specs/claims/spec.md`) no se modifica;
  `Apelacion` referencia a `Reclamacion` por FK.

## Approach

Reutiliza el patrón de CHG-205. `Apelacion` referencia a la
`Reclamacion` padre (no a `Solicitud`) para encadenar instancias.

**Estados**: `presentada` → `en_analisis` → `confirmada` |
`revocada` (terminales, excluyentes; equivalen a la "resolución
definitiva" de `§10.3`). Se descarta bool `confirma_decision_junta`
para mantener `TextChoices` consistentes con CHG-205.

**Reglas de negocio**:
1. **Precondición**: solo se apela si `Reclamacion` padre está
   `RESUELTA`/`RECHAZADA` y dentro del plazo.
2. **Plazo**: 30 días calendario desde notificación de la
   resolución (analogía CPACA / `§11.7` — a confirmar con R-OFIJUR
   en `sdd-spec`).
3. **Owner**: solo `R-ASPIRANTE` titular de la `Solicitud` puede
   crear.
4. **Resolución**: solo `R-OFIJUR` transiciona a `confirmada` o
   `revocada`.
5. **Auditoría**: toda transición registrada en
   `ApelacionHistorial`.

## Affected Areas

| Área | Impacto | Descripción |
|---|---|---|
| `apps/claims/models.py` | Modificado | `Apelacion`, `ApelacionHistorial` |
| `apps/claims/services/` | Modificado | `apelaciones_service.py` |
| `apps/claims/views.py` | Modificado | Create/List/Detail/AdminList/Resolve |
| `apps/claims/urls.py` | Modificado | Rutas con UUID |
| `apps/claims/templates/` | Nuevo | `create`, `list`, `detail`, `admin/list` |
| `apps/claims/admin.py` | Modificado | Registrar modelos |
| `apps/claims/tests.py` | Modificado | Modelo + transiciones + permisos |
| `apps/accounts/` | Modificado | Data migration crea `R-OFIJUR` |

## Dependencies

- **CHG-205** (Claims) — bloqueante, patrones base.
- **CHG-101** (Auth/RBAC) — base para registrar `R-OFIJUR`.
- `project.md §10.3`, `§11.7`, `§13.4`; CPACA Art. 76-77.

## Risks

| Riesgo | Probabilidad | Mitigación |
|---|---|---|
| Plazo para apelar no fijado para resultados | Media | 30 d.c. por analogía CPACA/§11.7; confirmar en `sdd-spec` |
| `R-OFIJUR` no existe como rol sembrado | Baja | Data migration idempotente con `get_or_create` |
| Sin notificaciones, cierre depende de acción manual | Alta | Documentado como follow-up; link "ver resolución" en detalle |

## Rollback Plan

1. Revertir migración de `Apelacion`/`ApelacionHistorial`.
2. Eliminar rol `R-OFIJUR` solo si no tiene `UserRole` asociados.
3. Revertir commits en `apps/claims/` (vistas, urls, templates).
4. No hay datos transaccionales a limpiar: modelo nuevo.

## Success Criteria

- [ ] `Apelacion` con UUID, FK a `Reclamacion`, FK a User
  (resuelto_por).
- [ ] `ApelacionHistorial` con estado_anterior/nuevo, actor,
  timestamp.
- [ ] Rol `R-OFIJUR` creado vía data migration.
- [ ] Aspirante puede apelar solo si `Reclamacion` padre está
  RESUELTA/RECHAZADA y dentro del plazo.
- [ ] R-OFIJUR ve lista global y resuelve a `confirmada` o
  `revocada` con respuesta fundamentada.
- [ ] Historial de transiciones registrado.
- [ ] Tests: modelo, transiciones, permisos, validaciones de
  precondición.
- [ ] `pytest --tb=short` pasa; `ruff check .` y `black --check .`
  limpios.
- [ ] Sin PII en fixtures; sin integraciones externas.
