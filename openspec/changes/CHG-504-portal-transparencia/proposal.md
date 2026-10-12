# CHG-504 — Portal de Transparencia (CAP-021)

## Contexto

CAP-021 (Portal de Transparencia / Datos Abiertos) es **P1** en
`project.md §8` y su entregable es el portal público que permite al
rol **R-CIUDA** acceder a datos abiertos sin autenticación profunda.
El groundwork existe:

- **`ListadoPublicoView`** (`apps/governance/views.py:274-314`): vista
  anónima en `/resultados/` que serializa ranking con PII ya
  sanitizado (solo posición y radicado, sin nombres ni documentos).
- **`ReportingService`** (`apps/reporting/services.py`): servicio
  interno (CHG-503, CAP-020) que calcula agregados sin PII y que
  puede reutilizarse.

El proposal de CHG-503 declaró explícitamente la deferencia del portal:

> *"**Fuera del alcance de este change**: portal público (CHG-504, §14.2),
> exportación a entes de control (CHG-505, §14.3), estudio de impacto
> (CHG-506)"*
> — `openspec/changes/CHG-503-reports/proposal.md:21` y `:72-75`

El marco legal aplicable es la **Ley 1581/2012** (protección de datos
personales) citada en `project.md §13.2` y la política PII de
`project.md §12.4`.

**Decisión de producto tomada por el usuario**:
1. **FIRST SLICE** = estadísticas agregadas solo por año/estado.
   El desglose por IES/municipio monetario queda explícitamente fuera
   del alcance (deferido a CHG-506 estudio de impacto).
2. El portal publica **tanto** páginas HTML públicas **como** endpoints
   JSON públicos (AllowAny, solo lectura) para datos abiertos.

## Capacidades afectadas

- **CAP-021** — Portal de Transparencia / Datos Abiertos (primaria)
- **CAP-020** — Reportes de Gestión (lectura de `ReportingService`,
  reutilización de agregados sin PII)

## Reglas de negocio afectadas

- `project.md §14.2` — Informes Públicos (R-CIUDA): convocatorias
  abiertas/cerradas, estadísticas agregadas, montos girados por
  año/IES/municipio (el desglose monetario IES/municipio se difiere a
  CHG-506)
- `project.md §12.4` — Listado de Beneficiarios: política PII;
  ninguna página del portal expone nombres, documentos ni datos
  sensibles de beneficiarios
- `project.md §13.2` — Protección de Datos Personales (Ley 1581/2012,
  Decreto 1377/2013): todo selector público garantiza enmascaramiento
  de PII en respuestas y logs
- `AGENTS.md §1` — Sin datos personales en código, fixtures,
  commits ni logs

## Cambios propuestos

### 1. Selectores públicos sin PII (`apps/reporting/`)

Se añaden selectores y lógica de preparación en `apps/reporting/` que
exponen únicamente datos agregados (sin nombres, documentos, emails ni
datos_academicos):

- `TransparenciaSelectors.actos_publicados()`: lista de actos con
  `estado=PUBLICADO`, sin nombres de beneficiarios, incluyendo enlace al
  PDF oficial.
- `TransparenciaSelectors.convocatorias_abiertas_cerradas()`: lista
  de convocatorias con su estado (EN_INSCRIPCION/CERRADA) y fechas.
- `TransparenciaSelectors.estadisticas_agregadas(anio=None,
  estado=None)`: reutiliza `ReportingService` para totales por año y
  estado — sin desglose IES/municipio en esta primera iteración.
- `TransparenciaSelectors.estadisticas_portal()`: compose de los KPIs
  públicos para la landing page.

### 2. Portal HTML público (`templates/transparencia/`)

Extienden `templates/base.html`. Ningún template expone nombres,
documentos ni datos de contacto:

- `templates/transparencia/base.html` — layout base del portal con
  navegación al portal.
- `templates/transparencia/index.html` — landing `/transparencia/` con
  resumen de cifras y accesos directos.
- `templates/transparencia/actos.html` — listado de actos
  administrativos publicados con paginación y enlace al PDF.
- `templates/transparencia/convocatorias.html` — listado de convocatorias
  abiertas y cerradas con fechas y enlaces.
- `templates/transparencia/estadisticas.html` — cifras agregadas por
  año/estado (primera iteración: sin IES/municipio).

### 3. API pública JSON (`/api/transparencia/`)

Endpoints read-only con `AllowAny` que exponen los mismos datos que
las páginas HTML en formato JSON para datos abiertos:

- `GET /api/transparencia/actos/` — actos publicados (serializador
  sin PII).
- `GET /api/transparencia/convocatorias/` — convocatorias con estado.
- `GET /api/transparencia/estadisticas/` — agregados por año y estado.
- `GET /api/transparencia/estadisticas/?anio=2026` — filtro por año.

### 4. URLs y navegación

- Routing en `apps/reporting/urls.py` (la app comparte app con
  CAP-020, no requiere app dedicada).
- Enlace "Transparencia" visible en la navegación de
  `templates/base.html` para usuarios autenticados e incógnitos.

## Criterios de aceptación

- [ ] `/transparencia/`, `/transparencia/actos/`,
  `/transparencia/convocatorias/`, `/transparencia/estadisticas/` son
  accesibles sin autenticación y devuelven HTTP 200.
- [ ] `/api/transparencia/actos/` devuelve únicamente actos con
  `estado=PUBLICADO`; actos en borrador o derogado no aparecen.
- [ ] Ninguna respuesta HTML ni JSON del portal contiene campos
  `nombre`, `documento`, `email`, `datos_beneficiario`,
  `datos_academicos` ni campos que identifiquen personalmente a un
  beneficiario.
- [ ] Los totales agregados en el portal coinciden con los valores
  calculados por `ReportingService` para los mismos filtros.
- [ ] Los tests de aserción PII-negativa (nombres, documento nunca en
  response) pasan en la suite del portal.
- [ ] La suite completa de pruebas (`pytest`) pasa en sqlite y
  PostgreSQL.

## Pruebas

- **Unitarias de selectores públicos**: cada selector devuelve solo
  campos documentados; aserción PII-negativa (nombres, emails,
  documentos nunca en resultado).
- **Integración HTML anónima**: `APIClient` sin autenticar accede a
  todas las páginas del portal → 200; no se requiere login.
- **Integración API anónima**: `APIClient` sin autenticar accede a
  todos los endpoints JSON → 200; no se requiere token.
- **Solo actos PUBLICADO**: test que crea acto en estado BORRADOR y
  verifica que no aparece en `/api/transparencia/actos/` ni en
  `/transparencia/actos/`.
- **PII-negative assertions**: patrón heredado de
  `test_reports.py:test_respuesta_sin_pii` — búsqueda de strings de
  datos sintéticos en la respuesta.
- **Suite completa**: verde en sqlite y PostgreSQL.

## Riesgos y Fuera del alcance

### Riesgos y mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| Exposición inadvertida de PII en el portal | Sanitización en capa de selector (nunca se consultan ni se serializan campos PII); tests de aserción negativa con datos sintéticos (patrón `test_reports.py:test_respuesta_sin_pii` línea ~189) |
| Parsing de `datos_academicos` (JSON) en agregaciones | Primera iteración excluye explícitamente `datos_academicos` del portal; se difiere a CHG-506 |
| Nombres de firmantes en metadata HTML | Los nombres de firmantes aparecen **solo** dentro del PDF oficial del acto, no en el HTML de listado ni en metadata |

### Fuera del alcance (declarados)

- Desglose de montos por IES/municipio (CHG-506 estudio de impacto).
- Exportación a entes de control sellada (CHG-505, `project.md §14.3`).
- Estudio de impacto bianual (CHG-506).
- Multidioma y trilingüismo (CHG-507).
- Auditoría de lecturas públicas (decisión abierta, diferida a CHG-505).
- Integraciones con sistemas externos (prohibido por `AGENTS.md §6` — Regla 2).
- Modificación de `project.md` para agregar capacidades nuevas.
