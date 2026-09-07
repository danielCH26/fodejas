# CHG-099 — Migración de datos previos (padrones, FUI físicos, resoluciones, listado 001-2025)

> **Convención de numeración**: este change usa `CHG-099`
> intencionalmente, no `CHG-208`. AGENTS.md §14 reserva el rango
> `CHG-099` para "change de migración de datos previo a Fase 2".
> Lo respetamos aunque la Fase 2 ya esté cerrada (CHG-201..208) —
> el rango sigue siendo válido para migraciones de datos previas
> a producción.

## Contexto

`roadmap.md §12` riesgo R8:
> "si se requiere migrar padrones, FUI físicos escaneados,
> resoluciones previas y el listado de la convocatoria 001-2025, esto
> debe hacerse como un change previo a la Fase 2
> (`CHG-099-migration`), respetando la regla de no incluir datos
> personales en el repo (los datos se cargan en la base
> transaccional, no en el repo de código)."

Para producir la primera convocatoria ("Reconocimiento a la
Excelencia 2026-1") y para demostrar cumplimiento histórico ante
la Oficina de Control Interno, la plataforma debe tener:

- Convocatorias previas (Convocatoria 001-2025 "Piloto Regional" y
  cualquier otra cerrada antes de la implementación).
- Solicitudes previas (los FUI físicos escaneados de la 001-2025).
- Resoluciones previas (actos administrativos firmados durante la
  001-2025).
- Listado definitivo previo (los beneficiarios adjudicados en la
  001-2025).

Esos datos **viven en los sistemas transaccionales de la Secretaría
de Educación** (Excel del año pasado, escaneos del drive
compartido, etc.), NO en el repo de código. AGENTS.md §6 regla 1
lo prohíbe explícitamente.

Este change provee el **framework de migración**: un comando de
gestión Django, schemas documentados, factories con datos sintéticos
para testing, y un manifiesto de qué archivos se esperan y dónde.
Los datos reales se cargan en una corrida controlada desde la ruta
proporcionada por el operador; no forman parte del repo.

## Capacidades afectadas

- **CAP-002** (Convocatorias — ciclo de estados): los datos
  migrados deben respetar el ciclo.
- **CAP-003** (FUI digital): los FUI migrados son réplicas
  históricas; deben marcarse como `MIGRADO` para distinguirlos de
  los digitales nativos.
- **CAP-008** (Resultados definitivos): los actos administrativos
  previos se migran en su estado final (`PUBLICADO` o `ANULADO`).

## Reglas de negocio afectadas

- `AGENTS.md §6` regla 1 (no escribir datos personales en
  fixtures, código, commits ni logs).
- `roadmap.md §12` R8 (migración de datos fuera del repo).
- `roadmap.md §12` R7 (mínimo privilegio, cifrado, DLP — la
  migración opera sobre la base transaccional, no sobre archivos
  planos persistidos).

## Cambios propuestos

### Delta en `specs/data-migration/spec.md` (nuevo spec)

#### ADDED — § Comando `migrate_legacy_data`

El proyecto SHALL exponer un comando de gestión Django
`python manage.py migrate_legacy_data` que ingiere datos legacy
desde un directorio configurable. El comando SHALL ser idempotente:
corridas repetidas con el mismo input NO SHALL crear duplicados
(búsqueda por clave natural: radicado de Solicitud, número de
acto, código de Convocatoria, etc.).

#### ADDED — § Schemas de los archivos de entrada

Cinco archivos CSV / JSON SHALL ser aceptados como input:

| Archivo | Modelo destino | Clave natural |
|---------|----------------|---------------|
| `convocatorias.csv` | `Convocatory` | `codigo` |
| `solicitudes.csv` | `Solicitud` | `radicado` |
| `usuarios_legacy.csv` | `CustomUser` | `documento` (anonimizado) |
| `actos_legacy.csv` | `ActoAdministrativo` | `numero` |
| `listados_legacy.csv` | `ListadoDefinitivo` | `convocatoria.codigo` |

Cada archivo DEBE respetar un header documentado en
`docs/migrations/data-schemas.md` (referencia a columnas
esperadas, tipos, nullability, anonimización).

#### ADDED — § Anonimización obligatoria

Cualquier campo que pueda contener PII (nombre, email, documento,
teléfono, dirección) DEBE pasarse por la función
`apps.core.migrations.anonymize()` antes de persistirse. La
anonimización reemplaza con `sha256(field + SECRET_SALT)[:12]`
para IDs reversibles-bajo-llave, o `None` para campos opcionales
donde el dato no es necesario para auditoría.

#### ADDED — § Validación previa

El comando DEBE validar antes de insertar:
1. Todos los archivos existen y son legibles.
2. Cada fila tiene su clave natural.
3. Las FKs entre archivos se satisfacen (ej. `Solicitud.convocatoria_codigo`
   debe existir en `convocatorias.csv`).
4. Ningún campo PII crudo está presente (regex check sobre las
   columnas sensibles).

Si la validación falla, el comando DEBE abortar SIN escribir
ningún registro, reportar la fila problemática y salir con código
de error 1.

### Cambios concretos

1. `apps/core/management/commands/migrate_legacy_data.py` (nuevo):
   comando Django con opciones `--source=<path>`, `--dry-run`,
   `--skip-validation`, `--anonymize-salt=<env-var>`.
2. `apps/core/migrations/anonymize.py` (nuevo): funciones de
   anonimización reversibles.
3. `apps/core/migrations/validators.py` (nuevo): validadores de
   schemas.
4. `apps/core/tests/factories.py` (nuevo): factories
   (`LegacyConvocatoriaFactory`, etc.) con datos sintéticos
   anonimizados por defecto.
5. `apps/core/tests/test_migrate_legacy_data.py` (nuevo): tests
   con factories, validación de schema, idempotencia.
6. `docs/migrations/data-schemas.md` (nuevo): documentación de
   los headers CSV/JSON esperados.
7. `docs/migrations/migration-runbook.md` (nuevo): procedimiento
   paso a paso para correr la migración en staging con datos
   reales (incluye checklist de anonimización).
8. `pyproject.toml`: agregar `factory-boy` (ya está) y confirmar
   dependencias.

## Criterios de aceptación

- [ ] El comando `python manage.py migrate_legacy_data --dry-run
      --source=<fixture_dir>` corre sin escribir a la DB y reporta
      conteos esperados.
- [ ] El comando con datos válidos crea Convocatorias, Solicitudes,
      CustomUsers, Actos y Listados en sus modelos correctos.
- [ ] El comando es idempotente: correrlo dos veces con el mismo
      input produce el mismo estado final (mismo conteo).
- [ ] El comando rechaza archivos mal formados con error legible.
- [ ] Ningún test contiene PII en fixtures ni asserts (verificado
      por grep sobre el directorio `apps/core/tests/`).
- [ ] La función `anonymize()` es reversible: con el mismo
      `SECRET_SALT`, el mismo input produce el mismo output.
- [ ] `docs/migrations/data-schemas.md` documenta el header exacto
      de cada CSV.
- [ ] `docs/migrations/migration-runbook.md` tiene un checklist de
      anonimización que el operador DEBE completar antes de la
      migración real.

## Pruebas

- Unitarias:
  - `apps/core/tests/test_migrate_legacy_data.py::test_dry_run_creates_no_records`
  - `apps/core/tests/test_migrate_legacy_data.py::test_idempotent`
  - `apps/core/tests/test_migrate_legacy_data.py::test_validation_aborts_on_bad_csv`
  - `apps/core/tests/test_migrate_legacy_data.py::test_anonymize_is_deterministic`
- Integración:
  - Con factories: crear 5 convocatorias + 20 solicitudes + 1 acto +
    1 listado, validar migración completa.
- Conformance:
  - `pytest apps/core/tests/ --no-header -q` corre limpio.
  - `grep -r "example.com\|1234567890\|CC \\|TI \\|@" apps/core/tests/`
    debe devolver 0 hits en campos de PII (los factories usan
    `anon-test-` como prefijo).

## Riesgos y Fuera del alcance

- **Riesgo**: el operador carga PII real en el repo por error al
  copiar CSVs. Mitigación: `.gitignore` para `data/`, `*.csv`,
  `*.jsonl` de migración; CI guard que rechaza PRs que contengan
  campos PII obvios.
- **Riesgo**: la anonimización es reversible con `SECRET_SALT`. Si
  el operador pierde el salt, los datos son irrecuperables. Esto es
  aceptable per AGENTS.md §6 (PII no se mezcla con la DB
  transaccional real).
- **Fuera del alcance**:
  - No se crea un ETL automatizado contra los sistemas transaccionales
    de la Secretaría — eso queda para `INF-005-secrets` (acceso
    controlado a bases externas) cuando exista un contrato de
    interoperabilidad.
  - No se incluyen los datos reales en el repo (per AGENTS.md §6).
  - No se rediseña ningún modelo existente; la migración usa los
    modelos tal como están.

## Referencias

- `roadmap.md §12` R8 (migración de datos fuera del repo).
- `AGENTS.md §6` regla 1 (no escribir datos personales).
- `apps/convocatories/models.py` (Convocatory).
- `apps/applications/models.py` (Solicitud).
- `apps/accounts/models.py` (CustomUser).
- `apps/governance/models.py` (ActoAdministrativo, ListadoDefinitivo).
- `docs/migrations/expand-contract.md` (preparado en CHG-804 —
  referencia cruzada para la metodología de migraciones).
