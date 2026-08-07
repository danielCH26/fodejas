# CHG-201-convocatory-engine — Motor de Convocatorias (CAP-002)

## Contexto

`CHG-104` dejó `Convocatory` con `estado` y
`ConfiguracionConvocatoria` — **falta el motor** del ciclo
`borrador→publicada→en_inscripcion→en_verificacion→en_calificacion→
definitiva→cerrada`. Sin él, "Reconocimiento a la Excelencia
2026-1" (`roadmap.md` Fase 2, `project.md` §12) **no arranca**.
Implementa **CAP-002** sobre CHG-104/101/102/103/106.

## Capacidades y Reglas

- **CAP-002 P0** (`project.md` §8); habilita CAP-003/004/005/008.
- `§7.4` (datos, no código); `§11` (criterios vía
  `get_receta_vigente`); `§12.2` (cronograma 2026-1).
- Toda transición → `AuditEvent` (CAP-022). Transiciones en
  `services/`/`domain/`, **nunca** en vistas (`AGENTS.md` §6.6).

## Cambios Propuestos

### 1. FSM (`domain/transitions.py`)

`TRANSICIONES_PERMITIDAS: dict[origen, set[destino]]` con los
8 estados (incluye `cancelada`).
`transicionar(c, destino, *, actor, motivo)` valida origen y
orquesta `AuditEvent`. Puro.

### 2. Servicios de etapa (`services/publicacion_service.py`)

`publicar(c, actor)` exige: origen `borrador`; receta vigente
con `full_clean()` verde (**delega** a CHG-104);
`receta["etapas"]` no vacía + fechas consistentes;
`created_by` resuelto. **No idempotente** — 2ª llamada falla
con `ValidationError` (preservar auditoría) y emite
`Notificacion` in-app (CHG-106).

Hermanos: `abrir/cerrar_inscripcion`, `abrir_verificacion`,
`abrir_calificacion`, `publicar_definitiva`, `cerrar`,
`cancelar`. `cerrar()` requiere `definitiva` con ≥1
beneficiario (CAP-008).

### 3. Admin, API y acoples

**Admin**: `list_display = (codigo, nombre, estado, periodo)`;
acciones `publicar`/`cerrar` **delegan al servicio**.

**API**: `POST /api/convocatorias/{id}/transicion/`
body `{destino, motivo}` → servicio;
`GET .../{id}/` read-only.
Permiso `convocatories.change_convocatory` + RBAC. **Sin**
endpoint público.

| Cap | CHG | Mecanismo |
| --- | --- | --- |
| CAP-022 | CHG-102 | `Convocatory` en `AUDIT_MODELS` |
| CAP-019 | CHG-106 | `Notificacion` in-app en hito |
| CAP-024 | CHG-104 | `get_receta_vigente` (no revalida) |

## Criterios y Pruebas

- [ ] Tests: 7 transiciones legales + 4 ilegales +
  predicados `publicar()`/`cerrar()`.
- [ ] `publicar()` sin receta/etapas → `ValidationError`
  específico.
- [ ] Cada transición → `AuditEvent` `action="TRANSITION"`,
  hash-chain válido.
- [ ] Notificaciones in-app en `publicada` y `cerrada`; admin
  sin mutación directa de `estado`.
- [ ] API: Coord. → 200, Aspirante → 403, destino inválido →
  400.
- [ ] `ruff`/`black` limpios; sin PII (§6.1); sin integración
  externa (§6.2).

## Affected Areas

| Área | Impacto |
| --- | --- |
| `apps/convocatories/domain/transitions.py` | Nuevo (FSM) |
| `apps/convocatories/services/publicacion_service.py` | Nuevo (servicios) |
| `apps/convocatories/admin.py` | Modificado (acciones delegadas) |
| `apps/convocatories/api/views.py`+`urls.py` | Nuevo (transición + GET) |
| `apps/convocatories/tests/` | Nuevo (FSM + svc + API + audit) |
| `apps/convocatories/README.md` | Modificado |

## Rollback, Deps y Entrega

`git revert` + `migrate convocatories zero` (sin migraciones
nuevas; `estado` ya existe). 2026-1 aún no opera.

CHG-104/101/102/103/106. **Sin** nueva dep ni integración
externa. **Single PR** a `develop` desde
`feat/convocatory-engine/CHG-201`, bajo 400 LOC
(`roadmap.md` §6).

## Decisiones Confirmadas

1. **Idempotencia `publicar()`**: NO — 2ª llamada falla.
2. **`cancelada`**: desde estados activos; NO desde `cerrada`.
3. **Listado público**: NO (CAP-021 = P1).
4. **Notificación de cierre**: obligatoria (acto administrativo).
