# CHG-103-catalogs — Catálogos Paramétricos del Dominio (CAP-023)

## Contexto

`apps/core/` está vacío (`models.py` y `admin.py` con 0 líneas). Las
capacidades CAP-002..CAP-030 (`project.md` §8) requieren listas
paramétricas —estrato, SISBÉN, etnia, municipio_isla, nivel_formación,
modalidad, tipo IES, tipo documento, etc.— actualmente dispersas o
inexistentes. Sin cat.Version normalizada, los modelos de
`apps/applications/`, `apps/convocatories/` y `apps/scoring/` deben
recrear choices incompatibles entre sí, lo que rompe la auditoría
(CAP-022) y la configuración por convocatoria (CAP-024).

`project.md` §7.4 deja explícito: *las reglas de convocatoria son
**datos**, no código*. Esta propuesta ejecuta esa directriz para las
listas maestras que esas reglas referencian.

## Capacidades Afectadas

- **CAP-023** — Catálogos Paramétricos (P0, `project.md` §8)
- Habilita **CAP-024** (Configuración de Reglas por Convocatoria)
- Prerrequisito blando para **CAP-002** (convocatorias) y **CAP-003**
  (FUI), ambos Fase 2.

## Reglas de Negocio Afectadas

- `project.md` §11.1 — requisitos 2, 3 (SISBÉN A/B/C, estratos 1-3, etnia Raizal, municipios del Archipiélago)
- `project.md` §11.3 — criterios ponderados (modalidad, nivel_formación, tipo IES)
- `project.md` §11.4 — duración por nivel (Art. 16 Decreto 0372/2025)
- No se viola §6.1 ni §8.1: SISBÉN/OCCRE siguen siendo verificación **manual/externa**, registrada como evidencia — los catálogos solo listan los valores aceptados.

## Cambios Propuestos

### 1. Modelo abstracto `CatalogoDominio` (apps/core/models.py)

Base reusable: `codigo` (único, slug), `nombre` (display), `descripcion`,
`orden`, `activo` (bool), `metadatos` (JSON validado). `__str__` devuelve
`nombre`. Manager `activos()` que filtra `activo=True`.

### 2. Catálogos concretos como modelos hermanos

| Modelo | Valores semilla |
| --- | --- |
| `Estrato` | 1, 2, 3, 4, 5, 6 |
| `GrupoSisben` | A, B, C, D |
| `Etnia` | Raizal, Afrodescendiente, Indígena, ROM, Ninguna |
| `MunicipioIsla` | San Andrés, Providencia, Santa Catalina |
| `NivelFormacion` | Técnico profesional, Tecnológico, Universitario pregrado, Especialización, Maestría, Doctorado |
| `ModalidadApoyo` | Crédito educativo condonable, Beca, Préstamo no condonable |
| `TipoIes` | Pública oficial, Pública no oficial, Privada |
| `TipoDocumento` | Cédula de ciudadanía, Cédula de extranjería, Tarjeta de identidad, Pasaporte, Permiso de protección temporal |
| `EstadoDocumento` | Pendiente, Aprobado, Rechazado, Subsanable |
| `CausalTerminacionConvenio` | Abandono, Bajo rendimiento, Sanciones, Cambio de programa, Fallecimiento, Otra |

### 3. Admin legible (apps/core/admin.py)

`@admin.register` por modelo: `list_display = (codigo, nombre, activo, orden)`,
`list_filter = (activo,)`, `search_fields = (codigo, nombre)`,
`ordering = (orden, nombre)`. Inline simple sin raw_id para admins de
Convocatoria (R-ADMIN, `project.md` §7.4).

### 4. Seed via data migration

`apps/core/migrations/0002_seed_catalogs.py` carga los valores de la
tabla §2. Idempotente (`get_or_create` por `codigo`). Sin PII
(AGENTS.md §6.1); solo códigos y nombres administrativos.

### 5. Selectors públicos

`apps/core/selectors.py`: `get_estratos_activos()`, `get_municipios_activos()`,
etc. Una función por catálogo. Consumidos por FUI (CAP-003) y motor de
scoring (CAP-005). Vive en `selectors/`, nunca embebido en vistas
(AGENTS.md §6.6).

## Criterios de Aceptación

- [ ] `pytest apps/core/` verde: tests de los 10 modelos, del manager `activos()`, del admin registrable, de la seed idempotente.
- [ ] `CatalogoDominio` no se migra a tabla propia (es abstracto); las 10 concretas sí.
- [ ] `manage.py loaddata` equivalente vía la migración produce exactamente los valores de la tabla §2.
- [ ] Las FK de `apps/applications/` (futuro CHG-202) referencian estos modelos, no `PositiveSmallIntegerField` ni `CharField` con `choices`.
- [ ] `audit_AuditEvent` (CAP-022) registra CREATE/UPDATE/DELETE sobre cada catálogo vía signals ya conectados.
- [ ] Sin PII en fixtures/commits/logs (AGENTS.md §6.1).
- [ ] `ruff check .` y `black --check .` limpios.

## Pruebas

- **Unit**: cada modelo hereda correctamente los campos; manager `activos()`; `__str__`; orden default por `orden`.
- **Integración**: data migration corre en `migrate` limpia y en DB ya sembrada (idempotencia).
- **Admin**: registración, filtros, búsqueda (smoke test del AdminSite).

## Riesgos y Fuera del Alcance

- **Fuera de alcance**: CRUD de catálogos vía API REST (solo vía admin en esta fase); versionado histórico de valores; i18n de los nombres (CAP-030, P3); sincronización con DANE/SISBÉN/OCCRE (prohibida — `project.md` §8.1); modelo `ConfiguracionConvocatoria` (CAP-024, propuesta aparte).
- **Riesgo bajo**: cambios futuros en valores semilla (e.g. nuevo estrato). Mitigación: `get_or_create` permite agregar sin romper DBs en producción.

## Affected Areas

| Área | Impacto | Descripción |
| --- | --- | --- |
| `apps/core/models.py` | Nuevo | `CatalogoDominio` abstracto + 10 modelos concretos |
| `apps/core/admin.py` | Nuevo | Registro legible de los 10 modelos |
| `apps/core/selectors.py` | Nuevo | Selectors por catálogo |
| `apps/core/migrations/0001_initial.py` | Nuevo | Esquema de los 10 modelos |
| `apps/core/migrations/0002_seed_catalogs.py` | Nuevo | Seed idempotente de la tabla §2 |
| `apps/core/tests/` | Nuevo | Unit + integration de catálogos |
| `apps/audit/signals.py` | Modificado | Conectar `post_save`/`post_delete` a los 10 nuevos modelos |
| Documentación | Nuevo | `apps/core/README.md` con cómo agregar un valor |

## Plan de Rollback

`git revert` en `develop` → `manage.py migrate core zero`. Sin
dependencias downstream en producción (este CHG es el primero que toca
`apps/core/`). Audit signals se desconectan automáticamente al borrar
los modelos.

## Dependencies

- `apps/audit/` (CAP-022) ya provee `post_save`/`post_delete` listos para conectar (CHG-102 archivado).
- Ninguna dependencia externa nueva.

## Modo de Entrega

**Single PR** hacia `develop`. Branch `feat/catalogs/CHG-103`. Tests
verdes local; smoke del admin en `runserver`. Sin migraciones
irreversibles.
