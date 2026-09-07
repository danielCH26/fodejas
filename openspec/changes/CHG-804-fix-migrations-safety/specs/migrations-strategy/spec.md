# Spec Delta — `migrations-strategy`

> Delta para CHG-804. Bloques `## ADDED` según plantilla OpenSpec.

## ADDED

### Requirement: Política expand/contract para cambios de PK o columnas con FKs existentes

Toda migración que altere una columna PK o cualquier columna referenciada por
foreign keys existentes **SHALL** seguir el patrón expand/contract de cuatro
pasos:

1. **Expand**: agregar la nueva columna como nullable
   (`AddField(..., null=True)`) sin tocar la columna original.
2. **Backfill**: una `RunPython` que itere sobre las filas existentes y
   copie/derive el nuevo valor. Para conversiones a UUID, **SHALL** usar
   `uuid.uuid5(NAMESPACE_URL, f"{table_name}:{old_pk}")` con un namespace
   documentado y estable.
3. **Swap**: la capa de aplicación pasa a leer la nueva columna (gated por
   setting o feature flag) y el schema hace `ALTER COLUMN ... SET NOT NULL`
   + creación de constraints FK sobre la nueva columna.
4. **Contract**: `RemoveField` sobre la columna original sólo después de
   verificar que no quedan readers y que los índices/FK están sobre la
   nueva.

El sistema **SHALL** registrar cada paso como una migración Django
independiente para que el grafo de dependencias refleje el orden real.

#### Scenario: Cambio de PK de BigAutoField a UUIDField

- **WHEN** un modelo referenciado por foreign keys activas cambia el tipo de
  su PK de `BigAutoField` a `UUIDField`,
- **THEN** el plan de migración debe contener al menos cuatro archivos
  (`expand`, `backfill`, `swap`, `contract`),
- **AND** la migración `backfill` **MUST** ser idempotente (re-ejecutable
  sin error ni cambio),
- **AND** la migración `backfill` **MUST** verificar el tipo actual de la
  columna antes de actuar y abortar sin escribir si la columna ya es
  `UUIDField`.

### Requirement: Backfill UUID determinístico para PKs históricos

El proyecto **SHALL** mantener una migración de backfill
(`apps/accounts/migrations/0008_backfill_uuids_customuser_role.py` y
`apps/convocatories/migrations/0003_backfill_uuids_convocatory.py`) que
garantice:

- Determinismo: la misma tupla `(table, old_pk)` produce siempre el mismo
  UUID.
- Idempotencia: ejecutar la migración N veces produce el mismo estado que
  ejecutarla una sola vez.
- Trazabilidad: el namespace usado es estable y está documentado en
  `docs/migrations/expand-contract.md`.
- No-op cuando la columna ya es `UUIDField` (estado actual del modelo en
  `develop` y `main`).

#### Scenario: Re-ejecución de la migración de backfill

- **WHEN** se ejecuta la migración 0008 de `accounts` sobre una base
  donde `accounts_customuser.id` ya es `UUIDField`,
- **THEN** la función `forward` no realiza escrituras,
- **AND** no se registran errores en el log de migraciones,
- **AND** el conteo de filas de `CustomUser` permanece invariante.

#### Scenario: Estado inconsistente entre environments

- **WHEN** un environment tiene la columna PK en `BigAutoField` y otro
  ya está en `UUIDField`,
- **THEN** la migración `backfill` actúa sólo sobre filas donde el PK es
  numérico (`isinstance(pk, int)`),
- **AND** nunca sobrescribe un PK que ya sea `uuid.UUID`.

### Requirement: Documentación del patrón expand/contract

El proyecto **SHALL** mantener `docs/migrations/expand-contract.md` con:

- Receta de 4 pasos (expand → backfill → swap → contract).
- Plantilla copy-paste de migración.
- Ejemplo guiado basado en `accounts.CustomUser`.
- Tabla histórica de migraciones destructivas previas (las tres de
  2026-07-17/18) y cómo la nueva migración de backfill las protege en
  futuros deploys.
- Procedimiento de reversión para migraciones UUID fallidas (forward-only
  repair con namespace alternativo).

El documento **MUST** estar enlazado desde `roadmap.md §4.1 INF-014`.

### Requirement: CI guard para migraciones destructivas

El workflow `.github/workflows/migrations-safety.yml` **SHALL**:

- Correr en cada `pull_request` y `push` a `main`/`develop`.
- Ejecutar `python manage.py makemigrations --check --dry-run` y fallar si
  se generan migraciones nuevas no commiteadas.
- Ejecutar un grep heurístico sobre los últimos 5 archivos de
  `apps/*/migrations/*.py`: si un archivo contiene `AlterField` con
  `primary_key=True` y no existe una migración posterior de backfill en
  el mismo app, el job falla.
- Subir el log/diff como artefacto cuando falla.

### Requirement: Anotación de migraciones destructivas existentes

Las migraciones `apps/accounts/migrations/0006_alter_customuser_id.py`,
`apps/accounts/migrations/0007_alter_role_id.py` y
`apps/convocatories/migrations/0002_alter_convocatory_id.py` **SHALL**
conservar su contenido operativo intacto (inmutabilidad del historial de
migraciones Django) y portar un comentario al tope del archivo que
referencie la nueva migración de backfill y la política INF-014.

#### Scenario: Migración 0006 anotada

- **WHEN** un lector abre `apps/accounts/migrations/0006_alter_customuser_id.py`,
- **THEN** las primeras líneas no vacías son un bloque de comentario que
  menciona CHG-804, la migración de backfill
  (`0008_backfill_uuids_customuser_role.py`) y la ruta
  `docs/migrations/expand-contract.md`,
- **AND** `operations` permanece idéntica al estado histórico.

### Requirement: Cobertura de pruebas para la migración de backfill

El proyecto **SHALL** mantener pruebas que:

- Verifiquen que `backfill_customuser_uuid`, `backfill_role_uuid` y
  `backfill_convocatory_uuid` son idempotentes (segunda llamada no
  rompe).
- Verifiquen que sobre un estado donde `pk` ya es `UUIDField`, la función
  es no-op.
- Verifiquen que el namespace es estable (mismo input → mismo UUID).
- Verifiquen reversibilidad de la migración 0008 de `accounts`
  (`migrate accounts 0007` → `migrate accounts 0008`).

Las pruebas **MUST NOT** incluir datos personales en fixtures ni en
inputs hardcodeados.
