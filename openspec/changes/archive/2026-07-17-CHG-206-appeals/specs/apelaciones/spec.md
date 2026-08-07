# Apelaciones (2ª instancia) — Specification

> Capability: **CAP-007** — App: `apps/claims/` — Change: CHG-206 (NEW)

## Purpose

Recurso administrativo de **2ª instancia** ante la **Oficina Jurídica de la Gobernación** (`R-OFIJUR`) contra decisiones de la Junta Directiva (CAP-006, 1ª instancia). Garantiza debido proceso CPACA. Anclaje: `project.md §10.3`, `§11.7`, `§13.4`. La 1ª instancia (`Reclamacion`) **no se modifica**: `Apelacion` referencia por FK.

## Requirements

### Requirement: Apelacion como recurso de 2ª instancia

Una `Apelacion` SHALL referenciar por FK la `Reclamacion` que apela y SHALL almacenar `uuid` para URL pública.

#### Scenario: Crear apelación contra reclamación terminal dentro de plazo
- GIVEN una `Reclamacion` en estado `RESUELTA` o `RECHAZADA` con `fecha_resolucion`
- AND un `R-ASPIRANTE` titular de la `Solicitud` vinculada
- AND menos de 30 días calendario desde `fecha_resolucion`
- WHEN presenta una apelación con descripción
- THEN SHALL crear la `Apelacion` en estado `presentada`
- AND SHALL registrar el evento inicial en `ApelacionHistorial`

### Requirement: Estados y transiciones

Una `Apelacion` SHALL tener estados `presentada`, `en_analisis`, `confirmada`, `revocada`. Transiciones SHALL:

| Desde | Evento | Hacia | Actor |
|-------|--------|-------|-------|
| `presentada` | `iniciar_analisis` | `en_analisis` | R-OFIJUR |
| `en_analisis` | `confirmar` | `confirmada` | R-OFIJUR |
| `en_analisis` | `revocar` | `revocada` | R-OFIJUR |

`confirmada` y `revocada` son **terminales y excluyentes** (resolución definitiva §10.3). Transiciones SHALL ser rechazadas si el actor no tiene el rol indicado o si el estado origen no es el esperado.

#### Scenario: R-OFIJUR resuelve la apelación con fundamentación
- GIVEN una `Apelacion` en estado `en_analisis`
- WHEN un `R-OFIJUR` confirma o revoca con `respuesta` no vacía
- THEN SHALL transicionar al estado terminal
- AND SHALL persistir `resuelto_por`, `fecha_resolucion`, `respuesta`
- AND SHALL escribir en `ApelacionHistorial`

#### Scenario: Resolver sin fundamentación o sin rol R-OFIJUR
- GIVEN una `Apelacion` en estado `en_analisis`
- WHEN un `R-OFIJUR` intenta transicionar con `respuesta` vacía
- OR WHEN un usuario sin rol `R-OFIJUR` intenta confirmar/revocar
- THEN SHALL rechazar la transición sin mutar `resuelto_por`

### Requirement: Precondición y plazo

El sistema SHALL aceptar la creación solo si (a) la `Reclamacion` padre está en estado `RESUELTA` o `RECHAZADA` con `fecha_resolucion`, **y** (b) la presentación ocurre dentro de los **30 días calendario** siguientes a esa fecha (`project.md §11.7`; CPACA Art. 76-77).

#### Scenario: Reclamación aún no terminal
- GIVEN una `Reclamacion` en `EN_REVISION` o `PRESENTADA`
- WHEN el titular intenta crear la apelación
- THEN SHALL rechazar por precondición

#### Scenario: Apelación extemporánea
- GIVEN `fecha_resolucion` de hace 31 días
- WHEN el titular intenta presentar
- THEN SHALL rechazar por extemporaneidad

### Requirement: Permisos de presentación

El sistema SHALL permitir crear solo al `R-ASPIRANTE` titular de la `Solicitud` vinculada. SHALL rechazar con 403 a cualquier otro usuario (incluido `R-OFIJUR` o `R-JUNTA`).

#### Scenario: Titular presenta
- GIVEN un `R-ASPIRANTE` titular
- WHEN presenta dentro de plazo
- THEN SHALL aceptar

#### Scenario: Usuario no titular intenta presentar
- GIVEN un usuario distinto del titular
- WHEN intenta presentar
- THEN SHALL rechazar con 403

### Requirement: Auditoría de transiciones

El sistema SHALL registrar toda transición en `ApelacionHistorial` con `estado_anterior`, `estado_nuevo`, `actor`, `timestamp`. SHALL incluir registro inicial con `estado_anterior=null` al crear.

#### Scenario: Historial al crear
- GIVEN una `Apelacion` recién creada
- WHEN el sistema completa la creación
- THEN SHALL existir en `ApelacionHistorial` un registro con `estado_anterior=null`, `estado_nuevo=presentada`, `actor=<creador>`

### Requirement: Existencia del rol R-OFIJUR

El sistema SHALL garantizar el rol `R-OFIJUR` vía data migration idempotente (`get_or_create`), patrón CHG-101.

#### Scenario: Migración idempotente
- GIVEN una base sin el rol `R-OFIJUR`
- WHEN se ejecuta la data migration
- THEN SHALL crear el rol sin duplicar al re-ejecutar

### Requirement: Visibilidad diferenciada

El sistema SHALL permitir al titular listar y ver sus apelaciones (estado, respuesta, enlace a la `Reclamacion` padre) y SHALL permitir a cualquier `R-OFIJUR` ver el listado global y el detalle para resolver.