# Delta — CAP-021 Portal de Transparencia / Datos Abiertos

> Capability: `openspec/specs/transparencia/spec.md`
> Parent capability: `openspec/specs/convocatories/spec.md`,
> `openspec/specs/governance/spec.md`, `openspec/specs/reporting/spec.md`
> Change: `openspec/changes/CHG-504-portal-transparencia/`
> Normative basis: `project.md §14.2`, `project.md §13.2`,
> `project.md §12.4`, `AGENTS.md §1`

## ADDED

### Requirement: Acceso público sin autenticación

El sistema SHALL exponer el portal de transparencia en la ruta
`/transparencia/` y sus subrutas (`/actos/`, `/convocatorias/`,
`/estadisticas/`) de modo que cualquier usuario — autenticado o no —
pueda acceder con HTTP 200, sin que se requiera login, token ni
credenciales.

El portal SHALL estar disponible también como API JSON read-only en
`/api/transparencia/` con `AllowAny` para consumo por terceros
(principio de datos abiertos).

#### Scenario: Acceso anónimo a página HTML

- **GIVEN** un usuario no autenticado
- **WHEN** solicita `GET /transparencia/`
- **THEN** la respuesta es HTTP 200 y se renderiza el template
  `transparencia/index.html`

#### Scenario: Acceso anónimo a API JSON

- **GIVEN** un cliente HTTP sin token
- **WHEN** solicita `GET /api/transparencia/estadisticas/`
- **THEN** la respuesta es HTTP 200 con JSON y sin desafío de
  autenticación

---

### Requirement: Publicación de actos administrativos en estado PUBLICADO

El sistema SHALL listar únicamente actos administrativos cuyo estado
sea `PUBLICADO`. Actos en estados `BORRADOR`, `VIGENTE` (no publicado)
o `DEROGADO` no SHALL aparecer en el portal ni en la API pública.

Cada acto publicado SHALL incluir: número de acto, fecha de
publicación, enlace al PDF oficial, y nombre de la convocatoria
asociada. Los nombres de los firmantes SHALL aparecer únicamente
dentro del documento PDF oficial, no en el HTML de listado ni en
metadatos de la API.

#### Scenario: Acto en borrador no visible

- **GIVEN** un acto con `estado = ActoAdministrativo.Estado.BORRADOR`
- **WHEN** se consulta `GET /api/transparencia/actos/`
- **THEN** el acto no aparece en la lista

#### Scenario: Acto publicado visible

- **GIVEN** un acto con `estado = ActoAdministrativo.Estado.PUBLICADO`
- **WHEN** se consulta `GET /api/transparencia/actos/`
- **THEN** la respuesta incluye el número, fecha, enlace al PDF y
  nombre de la convocatoria

---

### Requirement: Estadísticas agregadas sin datos personales

El sistema SHALL calcular y exponer estadísticas agregadas por año y
por estado de proceso, reutilizando los métodos de `ReportingService`
sin acceder a campos de identificación personal. Las respuestas SHALL
contener únicamente totales, conteos y proporciones — ningún nombre,
documento, email, teléfono, dirección ni `datos_academicos` de un
beneficiario individual SHALL ser serializado.

El desglose por IES o municipio SHALL quedar fuera del alcance de
esta primera iteración (deferido a CHG-506 estudio de impacto).

El portal SHALL cumplir la Ley 1581 de 2012 (protección de datos
personales, `project.md §13.2`) y la política de PII de
`project.md §12.4`.

#### Scenario: Estadísticas sin PII

- **WHEN** se obtiene `GET /api/transparencia/estadisticas/?anio=2026`
- **THEN** la respuesta no contiene los campos `nombre`, `documento`,
  `email`, `datos_beneficiario` ni `datos_academicos`

#### Scenario: Agregados por año

- **GIVEN** postulaciones en diferentes años y estados
- **WHEN** se filtra `?anio=2026`
- **THEN** la respuesta contiene totales correspondientes al año 2026
  y totales generales por estado

---

### Requirement: Listado de convocatorias públicas

El sistema SHALL exponer las convocatorias con estado `ABIERTA` y
`CERRADA` de forma pública, incluyendo: código, nombre, estado,
fecha de apertura y fecha de cierre. Las convocatorias en estado
`BORRADOR` o `CANCELADA` no SHALL ser visibles.

#### Scenario: Convocatoria abierta visible

- **GIVEN** una convocatoria con `estado = Convocatory.Estado.ABIERTA`
- **WHEN** se consulta `GET /api/transparencia/convocatorias/`
- **THEN** la respuesta incluye código, nombre, estado, fechas

#### Scenario: Convocatoria en borrador no visible

- **GIVEN** una convocatoria con `estado = Convocatory.Estado.BORRADOR`
- **WHEN** se consulta `GET /transparencia/convocatorias/`
- **THEN** la convocatoria no aparece en la página renderizada

---

### Requirement: Sanitización garantizada en capa de selector

El sistema SHALL garantizar que toda la lógica de exposición de datos
públicos resida en la capa de selectores (`selectors/`) y que los
serializadores y templates operen exclusivamente sobre los campos
expuestos por dichos selectores. Los campos de PII nunca SHALL ser
consultados en la capa de presentación del portal.

Los tests SHALL incluir aserciones negativas que busquen datos
sintéticos conocidos (nombres, emails, números de documento) en la
respuesta, siguiendo el patrón establecido en
`apps/reporting/tests/test_reports.py:test_respuesta_sin_pii`.

#### Scenario: Sombra de nombre en respuesta JSON

- **GIVEN** un usuario con nombre "Reportero Sintético" en la base de
  datos
- **WHEN** se consulta `GET /api/transparencia/estadisticas/`
- **THEN** la respuesta no contiene la cadena "Reportero"

#### Scenario: Documento en respuesta HTML

- **GIVEN** una persona con documento "6543219000"
- **WHEN** se renderiza `GET /transparencia/actos/`
- **THEN** el número de documento no aparece en el HTML
