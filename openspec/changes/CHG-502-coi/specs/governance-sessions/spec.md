# Delta — CAP-018 Conflictos de Interés

## ADDED

### Requirement: Declaración de conflicto por punto

El sistema SHALL permitir a un miembro de la sesión declarar un
conflicto de interés sobre un punto específico del orden del día, y
mientras el impedimento esté pendiente SHALL bloquear su voto en ese
punto.

#### Scenario: Voto bloqueado con impedimento pendiente

- **GIVEN** una declaración de conflicto PENDIENTE de un miembro sobre
  un punto
- **WHEN** el miembro intenta votar ese punto
- **THEN** el servicio rechaza el voto

### Requirement: Aprobación del impedimento

El sistema SHALL resolver el impedimento por mayoría simple (mitad + 1)
de los demás presentes con derecho a voto, excluyendo al declarante.

#### Scenario: Impedimento aprobado

- **WHEN** los votos a favor del impedimento alcanzan mitad + 1 de los
  presentes habilitados
- **THEN** la declaración queda APROBADA y el voto del declarante queda
  excluido de ese punto

#### Scenario: Impedimento rechazado

- **WHEN** los votos en contra del impedimento alcanzan mitad + 1 de
  los presentes habilitados
- **THEN** la declaración queda RECHAZADA y el declarante puede votar

#### Scenario: El declarante no vota el impedimento

- **WHEN** el miembro que declaró el conflicto intenta votar su propio
  impedimento
- **THEN** el servicio rechaza la operación

### Requirement: Auditoría de conflictos

El sistema SHALL registrar en la bitácora (CAP-022) la declaración, cada
voto de impedimento y la resolución.
