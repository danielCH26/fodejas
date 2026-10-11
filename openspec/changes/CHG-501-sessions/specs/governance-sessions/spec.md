# Delta — CAP-017 Sesiones de Junta y Comité Técnico

## ADDED

### Requirement: Convocatoria de sesiones

El sistema SHALL permitir convocar sesiones ordinarias (≥5 días hábiles
de anticipación) y extraordinarias (≥2 días hábiles) para la Junta
Administradora y el Comité Técnico, registrando fecha de convocatoria.

#### Scenario: Anticipo insuficiente

- **WHEN** se convoca una sesión ordinaria con 3 días hábiles de
  anticipación
- **THEN** el servicio rechaza la operación con error de negocio

#### Scenario: Sesión extraordinaria válida

- **WHEN** se convoca una sesión extraordinaria con 2 días hábiles
- **THEN** la sesión queda en estado CONVOCADA

### Requirement: Quórum

El sistema SHALL calcular el quórum como mitad + 1 de los miembros con
derecho a voto, y SHALL impedir abrir la sesión sin quórum.

#### Scenario: Apertura sin quórum

- **WHEN** se intenta abrir una sesión con menos de mitad + 1 miembros
  con derecho a voto presentes
- **THEN** el servicio rechaza la apertura

#### Scenario: Miembros por cargo no votan

- **GIVEN** un miembro exento por cargo (Gobernador, Alcalde o
  Secretario)
- **THEN** su asistencia se registra pero no cuenta para el quórum de
  votación ni puede emitir voto

### Requirement: Votación por punto

El sistema SHALL registrar votos (A_FAVOR/EN_CONTRA/ABSTENCION) por
miembro y punto, SHALL excluir los votos de miembros con conflicto de
interés declarado, y SHALL resolver cada punto por mayoría simple de los
votos emitidos.

#### Scenario: Voto excluido por conflicto

- **GIVEN** un miembro con conflicto declarado en un punto
- **THEN** su voto es rechazado por el servicio

#### Scenario: Mayoría simple

- **WHEN** un punto recibe más votos a favor que en contra
- **THEN** el punto queda APROBADO

### Requirement: Acta firmada

El sistema SHALL generar el acta de la sesión finalizada como documento
con hash SHA-256 y SHALL soportar su firma electrónica (CAP-029) antes
de archivarse.

#### Scenario: Acta con hash

- **WHEN** se finaliza una sesión
- **THEN** el acta se genera y almacena su hash SHA-256

### Requirement: Auditoría de sesiones

El sistema SHALL registrar en la bitácora (CAP-022) cada transición de
sesión, cambio de asistencia, voto y firma de acta.
