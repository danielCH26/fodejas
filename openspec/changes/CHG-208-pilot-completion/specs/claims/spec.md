# Spec Delta — `claims` (CHG-208)

> Delta para CHG-208. Bloques `## MODIFIED` según plantilla OpenSpec.

## MODIFIED

### Requirement: Lifecycle de Reclamación (CHG-205)

`Reclamacion` SHALL transicionar por los estados
`PRESENTADA → EN_REVISION → RESUELTA | DESESTIMADA`. Cada
transición SHALL registrarse en `ReclamacionHistorial` con
timestamp, actor, estado anterior y nuevo estado.

Una `RESUELTA` favorable SHALL habilitar la creación de una
`Apelacion` por el mismo `Solicitante` dentro del plazo
reglamentario (CPACA). Una `DESESTIMADA` SHALL agotar la vía
gubernativa y NO SHALL permitir la creación de Apelación.

`Reclamacion.estado` SHALL ser uno de los valores definidos en
`Reclamacion.Estado.TextChoices` (PRESENTADA, EN_REVISION,
RESUELTA, DESESTIMADA, VENCIDA).

#### Scenario: Reclamación PRESENTADA → RESUELTA

- **WHEN** un usuario `R-ASPIRANTE` crea una Reclamacion sobre su
      Solicitud,
- **THEN** la reclamación queda en `PRESENTADA`,
- **AND** la Junta la transiciona a `EN_REVISION`,
- **AND** la Junta resuelve favorable,
- **AND** el estado final es `RESUELTA` con `fecha_resolucion`
      registrada.

#### Scenario: Reclamación DESESTIMADA agota la vía

- **WHEN** la Junta resuelve desfavorablemente,
- **THEN** el estado final es `DESESTIMADA`,
- **AND** la vista de creación de Apelación SHALL rechazar la
      creación con HTTP 403.

### Requirement: Lifecycle de Apelación (CHG-206)

`Apelacion` SHALL transicionar por los estados
`INICIADA → EN_ANALISIS → CONFIRMADA | REVOCADA`.

Una `CONFIRMADA` SHALL ratificar la `Reclamacion.RESUELTA` original.
Una `REVOCADA` SHALL invalidar la decisión de primera instancia y
devolver el expediente a la Junta con orden de re-decisión.

`Apelacion` SHALL referenciar una `Reclamacion` previa en estado
`RESUELTA` (no SHALL poder apelarse una reclamación `DESESTIMADA`
o `VENCIDA`).

#### Scenario: Apelación confirmada ratifica primera instancia

- **WHEN** la Oficina Jurídica transiciona la Apelación a `CONFIRMADA`,
- **THEN** la `Reclamacion` original queda firme y definitiva,
- **AND** un evento de auditoría registra la confirmación.

#### Scenario: Apelación revocada invalida primera instancia

- **WHEN** la Oficina Jurídica transiciona la Apelación a `REVOCADA`,
- **THEN** la `Reclamacion.RESUELTA` queda invalidada,
- **AND** el expediente vuelve a la Junta con un evento de re-decisión
      generado (no implementado en este change — queda para
      `CHG-501-sessions`).
