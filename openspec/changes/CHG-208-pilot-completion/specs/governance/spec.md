# Spec Delta — `governance` (CHG-208)

> Delta para CHG-208. Bloques `## MODIFIED` / `## ADDED` según plantilla OpenSpec.

## MODIFIED

### Requirement: Workflow de actos administrativos

`ActoAdministrativo` SHALL transicionar por los estados
`BORRADOR → FIRMADO → PUBLICADO` exclusivamente a través de vistas
dedicadas:

- `ActoSignView` SHALL ser el único punto de transición
  `BORRADOR → FIRMADO`. Recibe los firmantes del cuerpo del request,
  valida que el acto esté en `BORRADOR`, persiste `estado=FIRMADO`,
  `firmantes=<lista>`, `fecha_firma=timezone.now()`. La transición
  SHALL ejecutarse dentro de `transaction.atomic` con
  `select_for_update()` sobre la fila del acto para serializar firmas
  concurrentes.
- `ActoPublishView` SHALL ser el único punto de transición
  `FIRMADO → PUBLICADO`. Rechaza con `HttpResponseBadRequest` (HTTP 400)
  cualquier intento de publicación de un acto en estado distinto a
  `FIRMADO`.

Una transición directa `BORRADOR → PUBLICADO` SHALL ser rechazada.
El cambio SHALL quedar registrado en el `LogEntry` de Django admin
(vía el audit signal CHG-801) para trazabilidad.

#### Scenario: Transición válida BORRADOR → FIRMADO → PUBLICADO

- **WHEN** un usuario con rol `R-JUNTA` envía POST a `actos/<uuid>/firmar/`
      con la lista de firmantes,
- **THEN** el acto pasa a `FIRMADO`, `firmantes` se persiste,
      `fecha_firma` queda registrada,
- **AND** un POST subsiguiente a `actos/<uuid>/publicar/` transiciona
      el acto a `PUBLICADO` y registra `fecha_publicacion`.

#### Scenario: Transición inválida (publicar sin firmar)

- **WHEN** un usuario envía POST a `actos/<uuid>/publicar/` con el
      acto en `BORRADOR`,
- **THEN** la vista SHALL rechazar con HTTP 400,
- **AND** el estado del acto SHALL permanecer en `BORRADOR`.

#### Scenario: Firmas concurrentes serializadas

- **WHEN** dos transacciones concurrentes intentan firmar el mismo
      acto simultáneamente,
- **THEN** sólo una SHALL persistir `estado=FIRMADO`,
- **AND** la otra SHALL recibir una excepción de concurrencia limpia
      (`OperationalError` en PostgreSQL con `select_for_update`,
      `ValueError` en SQLite sin bloqueo real).

## ADDED

### Requirement: Acto modificatorio (CPACA Art. 45)

Un `ActoAdministrativo` de tipo `MODIFICATORIO` SHALL referenciar un
acto original via FK `acto_original`. SHALL heredar el campo
`convocatoria` del original. La FK SHALL ser nullable (los actos
originales NO tienen `acto_original`).

SHALL requerirse rol `R-JUNTA` para crear un modificatorio.

Un modificatorio NO SHALL poder referenciar otro modificatorio
(cadena de un solo nivel: original → modificatorio). La vista de
creación SHALL validar `original.tipo != MODIFICATORIO` antes de
crear y rechazar con HTTP 400 si se viola.

El `numero` SHALL generarse vía `generar_numero_acto("modificatorio")`
para mantener secuencia anual separada del tipo `resolucion`.

#### Scenario: Creación válida de modificatorio

- **WHEN** un usuario `R-JUNTA` envía POST a
      `actos/<uuid:original>/modificatorio/` con campos válidos
      (`asunto`, `considerandos`, `resolutivo`),
- **THEN** se crea un nuevo `ActoAdministrativo` con
      `tipo=MODIFICATORIO`, `acto_original=<original>`,
      `convocatoria=<original.convocatoria>`,
      `numero=FODEJAS-YYYY-NNNNN` (de la secuencia de modificatorios),
      `estado=BORRADOR`.

#### Scenario: Modificatorio sobre otro modificatorio

- **WHEN** un usuario `R-JUNTA` intenta crear un modificatorio sobre
      un acto que ya es `MODIFICATORIO`,
- **THEN** la vista SHALL rechazar con HTTP 400 y un mensaje
      indicando que los modificatorios no pueden encadenarse.
