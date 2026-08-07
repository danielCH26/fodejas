# CHG-104-convocatory-config — Modelo de Configuración de Convocatoria (Receta) (CAP-024)

## Contexto

`project.md` §7.4 lo dice textual: *"las reglas de convocatoria son
**datos**, no código"*. Hoy `apps/convocatories/models.py` solo
contiene el stub `Convocatory(name)` (sin reglas, sin etapas, sin
requisitos). Las capacidades CAP-002 (publicación), CAP-004 (requisitos),
CAP-005 (scoring) y CAP-008 (resultados) necesitan una **receta
parametrizable** por convocatoria para operar: cada convocatoria
mezcla tipo, periodo, cupos, requisitos, scoring, cronograma y reglas
especiales (Providencia §11.5). Hardcodear eso rompe el principio
§7.4 y haría imposible operar dos convocatorias simultáneas con
reglas distintas sin redeploy.

Esta propuesta implementa **CAP-024** (P0) — el modelo de
configuración tipo "receta" — y deja listo el suelo para los CHG
siguientes de CAP-002..CAP-008.

## Capacidades Afectadas

- **CAP-024** — Configuración de Reglas por Convocatoria (P0, `project.md` §8).
- Habilita: **CAP-002** (publicación), **CAP-004** (validación de requisitos), **CAP-005** (scoring), **CAP-008** (resultados definitivos).
- Prerrequisito: **CAP-023** (catálogos paramétricos en `apps/core/`, archivado en CHG-103).
- Consume signals de **CAP-022** (auditoría, archivado en CHG-102).

## Reglas de Negocio Afectadas

- `project.md` §7.4 — reglas son datos, no código.
- `project.md` §11.3 — criterios de calificación (peso por defecto: 50/30/20).
- `project.md` §11.4 — duración por nivel (Art. 16 Decreto 0372/2025): técnico 3a, tecnológico 4a, pregrado 6a, esp./maestría 2a, doctorado 5a; beneficio 5a (10 semestres).
- `project.md` §11.5 — regla de excepción de Providencia Isla (segundo mejor si el primero ya tiene beneficio similar).
- `project.md` §2.9 — SMLMV y montos configurables.
- `project.md` §12 — convocatoria de referencia (línea base a reproducir sin código nuevo).

## Cambios Propuestos

### 1. Modelo `Convocatory` ampliado (`apps/convocatories/models.py`)

Extender el stub existente con campos definitivos para cubrir CAP-024:
`nombre`, `codigo` (slug único), `tipo` (choices: cerrada, publica,
mérito, vulnerabilidad, area_prioritaria), `periodo` (CharField
descriptivo), `fecha_apertura`, `fecha_cierre`,
`fecha_publicacion_preliminar`, `fecha_publicacion_definitiva`,
`modalidad_apoyo` (FK a `core.ModalidadApoyo`), `monto_semestre_smlmv`
(Decimal, default 5; §2.9), `duracion_maxima_semestres` (PositiveInt),
`cupo_total` (PositiveInt), `estado` (TextChoices: borrador, publicada,
en_inscripcion, en_verificacion, en_calificacion, definitiva, cerrada,
cancelada), `created_by` (FK a `accounts.User`), `created_at`,
`updated_at`. Manager `activas()` que filtra por estados ejecutables.
`ConfiguracionConvocatoria` se referencia 1→1 (ver §2).

### 2. Modelo `ConfiguracionConvocatoria` — la "Receta" (`apps/convocatories/models.py`)

Modelo central: `convocatoria` (OneToOne FK a `Convocatory`),
`version` (PositiveInt, default 1), `schema_version` (Char — p.ej.
"1.0.0" para migraciones de payload), `payload` (JSONField con JSON
Schema validado en `clean()` y `full_clean()`), `descripcion`,
`created_by`, `created_at`, `valida_hasta` (DateTime null — fecha
desde la cual se considera histórica). Constraint
`unique_together = ("convocatoria", "version")`.

`payload` tiene la siguiente forma (validada con `jsonschema`):

```json
{
  "etapas": [
    {"id": "inscripcion", "orden": 1, "fecha_inicio": "...",
     "fecha_fin": "...", "responsable": "aspirante"},
    {"id": "verificacion", "orden": 2, "fecha_inicio": "...",
     "fecha_fin": "...", "responsable": "coord"}
  ],
  "requisitos_minimos": [
    {"id": "egresado_ie", "descripcion": "Egresado IE del Archipiélago",
     "medio_verificacion": "acta_grado", "responsable": "junta",
     "obligatorio": true}
  ],
  "tipos_documento_requeridos": [
    {"tipo": "acta_grado", "obligatorio": true, "vencimiento_dias": null}
  ],
  "criterios_calificacion": [
    {"id": "merito_academico", "peso": 50,
     "fuente": "acto_administrativo"},
    {"id": "condicion_socioeconomica", "peso": 30,
     "fuente": "sisben_o_estrato"},
    {"id": "etnia_residencia", "peso": 20, "fuente": "occre"}
  ],
  "cupos": [
    {"municipio_codigo": "SAN_ANDRES", "modalidad_codigo": "CEC",
     "nivel_codigo": "PREGRADO", "cantidad": 10},
    {"municipio_codigo": "PROVIDENCIA", "modalidad_codigo": "CEC",
     "nivel_codigo": "PREGRADO", "cantidad": 2,
     "regla_especial": "providencia_segundo_mejor"}
  ],
  "plazos_normativos": {
    "duracion_maxima_semestres": 10,
    "plazos_por_nivel": {
      "TECNICO": 6, "TECNOLOGICO": 8, "PREGRADO": 12,
      "ESPECIALIZACION": 4, "MAESTRIA": 4, "DOCTORADO": 10
    }
  },
  "reglas_especiales": {
    "providencia_isla": {
      "aplica": true,
      "ref_art_normativo": "Art. 15 Ordenanza 007/2025"
    }
  }
}
```

### 3. Validador de payload (`apps/convocatories/domain/validators.py`)

Función `validar_receta(payload: dict, schema_version: str) -> None`
que dispara `ValidationError` si:

- Algún peso en `criterios_calificacion` no suma **exactamente 100**.
- Algún FK lógico (municipio/modalidad/nivel) referencia un código
  inactivo del catálogo `apps/core/` (CAP-023).
- `duracion_maxima_semestres` no coincide con `plazos_por_nivel` del
  nivel elegido y la convocatoria está publicada.
- `reglas_especiales.providencia_isla` referencia un artículo
  normativo que no existe en el catálogo normativo embebido (ver §6).
- Schema version desconocido → error de migración requerido.

Invocada en `ConfiguracionConvocatoria.full_clean()` y desde el
servicio `clonar_receta()` antes de persistir. **Lógica de dominio,
no de vista** (AGENTS.md §6.6).

### 4. Servicio de clonado/versión (`apps/convocatories/services/receta_service.py`)

`clonar_receta(convocatoria_origen) -> ConfiguracionConvocatoria` que
incrementa `version`, copia `payload`, valida, registra en auditoría.
Necesario porque una receta debe versionarse sin perder la trazabilidad
de cuál rigió cada convocatoria (CAP-022).

### 5. Selectors públicos (`apps/convocatories/selectors.py`)

`get_receta_vigente(convocatoria_id)` → última versión activa de la
receta. Consumido por CAP-002 (publicación), CAP-004 (validación),
CAP-005 (scoring). Vive en `selectors/`, nunca embebido en vistas
(AGENTS.md §6.6).

### 6. Catálogo normativo embebido (`apps/convocatories/domain/normativa.py`)

Diccionario inmutable de referencias normativas citadas por las reglas
especiales (llaves = `Art. X Ordenanza 007/2025`, valores = descripción
corta). El validador §3 compara contra este catálogo para evitar
citas inventadas (AGENTS.md §6.4 / `config.yaml` `rules.proposal`).

### 7. Seed de la receta "Reconocimiento a la Excelencia 2026-1"

`apps/convocatories/migrations/0002_seed_receta_excelencia_2026_1.py`
carga el `payload` que reproduce exactamente la convocatoria de
referencia (`project.md` §12): 50/30/20, 10 candidatos SABER 11,
Providencia excepción habilitada, cupo total configurado. Idempotente
(`get_or_create` por `convocatoria+version`). Sin PII
(AGENTS.md §6.1).

### 8. Admin legible (`apps/convocatories/admin.py`)

`ConvocatoryAdmin`: `list_display = (codigo, nombre, tipo, estado,
periodo)`, `list_filter = (estado, tipo)`, `search_fields = (codigo,
nombre)`.
`ConfiguracionConvocatoriaAdmin`: `list_display = (convocatoria,
version, schema_version, valida_hasta)`. `payload` se muestra en
`raw_id_fields` opcional con `format_html` colapsable — sin
`JSONField` editable directo para evitar edición fuera del servicio.

### 9. Audit signals (sin nueva infra)

CAP-022 ya está conectado vía signals (`apps/audit/signals.py`,
CHG-102). Este CHG solo agrega `Convocatory` y `ConfiguracionConvocatoria`
al registro `AUDIT_MODELS` para que sus CRUD queden en bitácora sin
código nuevo en el signal.

## Criterios de Aceptación

- [ ] `pytest apps/convocatories/` verde: tests del modelo ampliado, del validador (suma 100, catálogos inactivos, plazos §11.4, Providencia §11.5), del servicio de clonado/versión, del selector `get_receta_vigente`, de la seed idempotente.
- [ ] `get_receta_vigente(convocatoria_id)` devuelve la receta con `valida_hasta` nulo o futuro.
- [ ] `clonar_receta()` incrementa `version`, no muta la anterior, crea evento `UPDATE` en auditoría.
- [ ] Payload inválido (suma ≠ 100) rechaza `full_clean()` con `ValidationError` específico.
- [ ] FKs lógicas a `apps/core/` validan contra catálogos inactivos.
- [ ] Seed `0002` carga la receta de §12 exactamente; idempotente.
- [ ] `Convocatory` y `ConfiguracionConvocatoria` aparecen en `AuditEvent` con action CREATE/UPDATE/DELETE.
- [ ] Sin PII en fixtures/commits/logs (AGENTS.md §6.1).
- [ ] `ruff check .` y `black --check .` limpios.

## Pruebas

- **Unit**: campos y managers de `Convocatory`; constraint unique en `Convocatory.codigo`; `__str__`.
- **Unit validador**: payloads buenos y malos (suma 100 OK, suma 99 falla; código catálogo inactivo falla; `regla_especial` sin art. normativo falla; schema_version desconocido falla).
- **Service**: `clonar_receta` incrementa version, no muta origen, registra auditoría.
- **Selector**: `get_receta_vigente` retorna la última vigente; ignora versiones con `valida_hasta` pasada.
- **Integración seed**: `0002` corre en DB limpia y en DB ya sembrada (idempotencia).
- **Audit smoke**: CRUD sobre ambos modelos genera `AuditEvent` con la entidad correcta (CHG-102 ya cubre la infra).

## Riesgos y Fuera del Alcance

- **Fuera de alcance**: UI de edición de receta vía wizard (P1, propuesta aparte con HTMX + Alpine); exportación de receta como PDF/resolución; comparador de versiones (CHG-205+); modelado de `Hito` y `Cupo` como entidades independientes (en esta propuesta viven dentro del JSON; pueden normalizarse en un CHG futuro si el JSONSchema se queda corto); scoring motor (CAP-005 consume el payload pero su ejecución es otro CHG); versionado visual en admin.
- **Riesgo medio**: JSONField mal validado en producción. Mitigación: doble gate (`full_clean` + servicio), `schema_version` para migraciones de payload, catálogo normativo embebido como fuente única de citas.
- **Riesgo bajo**:.payload crece demasiado y degrada el admin. Mitigación: vista colapsable + extraer sub-objetos como tablas en CHG futuro si supera ~20 keys top-level.

## Affected Areas

| Área | Impacto | Descripción |
| --- | --- | --- |
| `apps/convocatories/models.py` | Modificado | Reemplaza stub; añade `Convocatory` definitivo + `ConfiguracionConvocatoria` |
| `apps/convocatories/domain/validators.py` | Nuevo | `validar_receta()` con JSON Schema + reglas de negocio |
| `apps/convocatories/domain/normativa.py` | Nuevo | Catálogo inmutable de citas normativas |
| `apps/convocatories/services/receta_service.py` | Nuevo | `clonar_receta()`, versionado |
| `apps/convocatories/selectors.py` | Nuevo | `get_receta_vigente()` y selectores auxiliares |
| `apps/convocatories/migrations/0001_initial.py` | Nuevo | Esquema de los 2 modelos |
| `apps/convocatories/migrations/0002_seed_receta_excelencia_2026_1.py` | Nuevo | Seed idempotente de §12 |
| `apps/convocatories/admin.py` | Modificado | Registra los 2 modelos con vista colapsable del payload |
| `apps/convocatories/tests/` | Nuevo | Unit validador + service + selector + smoke auditoría |
| `apps/audit/signals.py` | Modificado | Agrega `Convocatory` y `ConfiguracionConvocatoria` a `AUDIT_MODELS` |
| `pyproject.toml` | Modificado | Añade `jsonschema>=4.21` (dep nueva única) |
| Documentación | Nuevo | `apps/convocatories/README.md` — cómo clonar/editar una receta |

## Plan de Rollback

`git revert` en `develop` → `manage.py migrate convocatories zero` →
desregistrar modelos en `apps/audit/signals.py`. Sin dependencias
downstream en producción (este CHG es el primero que materializa
CAP-024 y CAP-002 aún no corre). Si la receta ya estaba en uso real
para alguna convocatoria piloto, exportar antes del revert el `payload`
a S3 como respaldo de bitácora (Ley 1581/2012, retención 20a).

## Dependencies

- `apps/core/` con los 10 catálogos de CHG-103 (archivado, FKs lógicas ya disponibles).
- `apps/audit/` con signals de CHG-102 (archivado, registrar modelos en `AUDIT_MODELS`).
- `apps/accounts/` con `accounts.User` de CHG-101 (archivado, FK en `created_by`).
- Nueva dep `jsonschema>=4.21` (única adición a `pyproject.toml`).
- **Sin integración externa** nueva. Verificación manual/externa conforme `project.md` §1.4 / §8.1.

## Modo de Entrega

**Single PR** hacia `develop`. Branch `feat/convocatory-config/CHG-104`.
Tests verdes local; smoke del admin en `runserver` mostrando la receta
de §12. Sin migraciones irreversibles (`migrate convocatories zero`
es reversible porque no hay datos downstream).

## Decisiones Confirmadas

1. **Granularidad de `Hito`/`Cupo`**: **TABLAS** — se normalizan como modelos
   separados desde el inicio para permitir queries SQL directas (e.g. "todos
   los cupos de Providencia").
2. **`schema_version` del payload**: **CON VERSIONADO** — se implementa historial
   de versiones (`ConvocatoriaVersion`) para poder revertir cambios.
3. **Edición vía admin**: **INTERFAZ GRÁFICA** — admin editable con validación,
   no solo lectura. La edición directa está permitida con validaciones.
