# Spec — convocatory-engine (CAP-002)

> Motor de ciclo de vida sobre `Convocatory`/`ConfiguracionConvocatoria` (CHG-104). CAP-002 P0; habilita CAP-003/004/005/008.

## Requirements

### Requirement: Convocatory Model — Estado Mutation Guard

`Convocatory.estado` SHALL ser mutable **solo** vía servicio.
Escrituras directas SHALL lanzar `ValidationError`. Solo
lectura: `transiciones_permitidas`,
`puede_transicionar_a?(destino)`.
(Previously: `estado` editable; sin FSM.)

#### Scenario: Admin bloquea; service muta atómico

- GIVEN `Convocatory` `borrador`
- WHEN R-COORD abre el form o un shell hace
  `c.estado="publicada"; c.save()`
- THEN `estado` en `readonly_fields`; ORM lanza
  `ValidationError`; `audit permission_denied`
- AND `publicar(c, actor)` cierra `transaction.atomic()`
- THEN `audit` registra **una** fila `action="TRANSITION"`
  con `{from, to, motivo}`; `post_save` no duplica

### Requirement: Finite State Machine (FSM)

`domain/transitions.py` SHALL definir `TRANSICIONES_PERMITIDAS`:

| Origen                 | Destinos                       |
| ---------------------- | ------------------------------ |
| `borrador`             | `publicada`, `cancelada`        |
| `publicada`            | `en_inscripcion`, `cancelada`   |
| `en_inscripcion`       | `en_verificacion`, `cancelada`  |
| `en_verificacion`      | `en_calificacion`, `cancelada`  |
| `en_calificacion`      | `definitiva`, `cancelada`       |
| `definitiva`           | `cerrada`                       |
| `cerrada`, `cancelada` | (terminal)                      |

`transicionar(c, destino, *, actor, motivo)` SHALL ser pura:
valida origen↦destino, lanza `ValidationError` si no aplica,
persiste + emite `AuditEvent` en `transaction.atomic()`.
`cancelada` SHALL ser destino **solo** desde estados activos.
Lógica en `domain/`, no en vistas (`AGENTS.md` §6.6).

#### Scenario: Legal avanza / ilegal o terminal rechaza

- GIVEN `Convocatory` `borrador`, R-COORD
- WHEN `transicionar(c, "publicada", actor=u, motivo="OK")`
- THEN `estado="publicada"`; `audit TRANSITION` hash-chain válido
- AND transición ilegal o desde estado terminal
- THEN `ValidationError`; sin cambios; sin `audit`

### Requirement: Services — `publicar`, `cerrar`, `cancelar`

`publicar(c, actor)` SHALL exigir `estado="borrador"`,
`get_receta_vigente(c.id)` (CHG-104) verde, `etapas`
válido, `created_by`. **NO idempotente**. Éxito SHALL
emitir `Notification` in-app vía `NotificationPort`
(CHG-106) `event="convocatory.publicada"`.

`cerrar(c, actor)` SHALL exigir `estado="definitiva"`,
`count_beneficiarios(c.id)>=1` (CAP-008), `created_by`.
Éxito SHALL emitir `Notification` `event="convocatory.cerrada"`
(acto adm.).

`cancelar(c, actor, motivo)` SHALL exigir estado activo y
`motivo` no vacío; `Notification` `tipo="warning"`.

#### Scenario: éxito y errores de predicado

- GIVEN `borrador` con receta y `created_by`
- WHEN `publicar(c, u)`
- THEN `estado="publicada"`; `audit TRANSITION`;
  Notification watchers; PII enmascarada CHG-106
- AND predicados fallidos
- WHEN `publicar|cerrar|cancelar(c, ...)`
- THEN `ValidationError` simbólico: `receta vigente requerida
  (CAP-024)`, `receta.etapas_invalidas`, `origen debe ser
  borrador`, `definitiva sin beneficiarios (CAP-008)`,
  `motivo requerido`, FSM §terminal; `audit
  action="convocatory.publish_failed"` solo el 1.º
- AND `definitiva` con ≥1 beneficiario
- WHEN `cerrar(c, u)`
- THEN `estado="cerrada"`; `audit TRANSITION`;
  Notification `convocatory.cerrada`

### Requirement: API REST — Transitions (RBAC CAP-001)

| Método | Path                                  | Permiso                                   |
| ------ | ------------------------------------- | ----------------------------------------- |
| POST   | `/api/convocatorias/{id}/transicion/` | `convocatories.change_convocatory` scoped |
| GET    | `/api/convocatorias/{id}/`            | lectura scoped (R-COORD/R-CT/R-ADMIN)      |

POST SHALL aceptar `{destino, motivo}` y delegar al servicio:
`200` `{estado_actual, transicion}`; `400` destino inválido /
motivo vacío; `403`; `404`. **Sin** endpoint público (CAP-021
P1). GET SHALL devolver read-only `{id, codigo, nombre, tipo,
periodo, estado, transiciones_permitidas[]}`.

#### Scenario: 200 / 403 / 400

- GIVEN R-COORD scoped en X (`publicada`)
- WHEN POST `.../transicion/`
  `{"destino":"en_inscripcion","motivo":"apertura"}`
- THEN `200` `{estado_actual:"en_inscripcion"}`; `audit`
- AND usuario sin rol scoped / destino FSM ilegal / id inexistente
- WHEN POST con cada uno
- THEN `403` / `400 {"destino":"transición inválida..."}` /
  `404`; `audit` solo en 403

### Requirement: Admin — State Management

`ConvocatoryAdmin.list_display SHALL=(codigo, nombre, estado,
periodo)`; `list_filter=(estado, tipo)`;
`search_fields=(codigo, nombre)`. `estado` SHALL estar en
`readonly_fields`. Acciones bulk `publicar`/`cerrar` SHALL
delegar al servicio, ejecutar en `transaction.atomic()`
por item, registrar `audit` por cada uno y emitir **una sola**
`Notification` agrupada con `payload["count"]=N`.

#### Scenario: Acción publicar masiva

- GIVEN 5 `borrador` con receta válida seleccionadas
- WHEN R-COORD aplica acción `publicar`
- THEN las 5 transitan; 5 filas `audit TRANSITION`; una sola
  Notification agrupada `event="convocatory.publicada"`
  con `count=5`; las que fallen se reportan sin transicionar

## Constraints

- Transiciones MUST residir en `services/`/`domain/`
  (`AGENTS.md` §6.6); vista/template no muta `estado`.
- `publicar`/`cerrar` NO son idempotentes.
- `Notification` obligatoria en `publicada`/`cerrada`
  (acto adm.).
- `audit.AuditEvent.ACTION_CHOICES` SHALL incluir
  `"TRANSITION"` y `"convocatory.publish_failed"` (CAP-022).
- Sin PII; sin integración externa; plazos
  `Decreto 0372/2025 Art. 16` / `project.md` §12.2.
