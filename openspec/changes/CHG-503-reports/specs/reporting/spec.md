# Delta — CAP-020 Reportes de Gestión

## ADDED

### Requirement: Informe de gestión por periodo

El sistema SHALL generar un informe de gestión para un año y trimestre
(o año completo) que componga: postulaciones por convocatoria con
desglose por estado, beneficiarios legalizados por convocatoria,
ejecución presupuestal del periodo (ordenado/pagado/pendiente) y
seguimiento académico con tasa de graduación.

#### Scenario: Informe trimestral

- **WHEN** se solicita el informe del trimestre 3 de 2026
- **THEN** la respuesta contiene los KPIs de §14.1 agregados en el
  rango de fechas del trimestre

#### Scenario: Informe anual

- **WHEN** se solicita el informe anual 2026 sin trimestre
- **THEN** la respuesta agrega el año completo

### Requirement: Acceso restringido sin PII

El sistema SHALL restringir los informes internos a los roles R-COORD,
R-JUNTA y R-ADMIN, y las respuestas SHALL contener únicamente agregados
(sin nombres, emails ni documentos).

#### Scenario: Rol sin acceso

- **WHEN** un usuario con rol R-ASPIRANTE solicita el informe
- **THEN** la API responde 403

#### Scenario: Sin PII

- **WHEN** se obtiene un informe
- **THEN** la respuesta no contiene emails, nombres ni documentos de
  identidad
