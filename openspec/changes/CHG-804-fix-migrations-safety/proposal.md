# CHG-804 — Seguridad de migraciones (expand/contract + backfill UUID en PKs)

## Contexto

La auditoría completa del 2026-09-05 (`docs/audits/extended-audit.md`
AUD-019 CRITICAL) detectó tres migraciones recientes que cambian el
tipo de PK de `BigAutoField` a `UUIDField` en tablas que ya tienen
FKs referenciadas:

- `apps/accounts/migrations/0006_alter_customuser_id.py`
  (2026-07-17) — `CustomUser`.
- `apps/accounts/migrations/0007_alter_role_id.py`
  (2026-07-18) — `Role`.
- `apps/convocatories/migrations/0002_alter_convocatory_id.py`
  (2026-07-18) — `Convocatory`.

Estas migraciones son schema-only `AlterField`. Con datos existentes
en PostgreSQL, `ALTER TABLE ... ALTER COLUMN id TYPE UUID USING ...`
rompe las FKs que apuntan a esas tablas o requiere un `USING` explícito
que las tres migraciones no declaran. No hay data migration que
backfille los nuevos UUIDs determinísticamente. No siguen el patrón
expand/contract que `roadmap.md:180` (INF-014) y el proyecto declaran
como política.

AGENTS.md §6 regla 5 (integridad transaccional) y §6 regla 9 (no
romper trazabilidad) están en riesgo mientras estas migraciones sigan
siendo destructivas sin un plan de rollback real.

## Capacidades afectadas

- **INF-014** (Estrategia de migraciones, `roadmap.md:180`).
- **CAP-001** (auth/RBAC — `CustomUser` y `Role` son auth).
- **CAP-002** (convocatorias — `Convocatory`).

## Reglas de negocio afectadas

- `AGENTS.md` §6 regla 5 (integridad transaccional).
- `AGENTS.md` §6 regla 9 (no romper trazabilidad).
- `roadmap.md` §4.1 INF-014 (zero-downtime deploys, expand/contract).
- `project.md` §12 R10 (indisponibilidad de DB → backups + monitoreo).

## Cambios propuestos

### Delta en `specs/migrations-strategy/spec.md`

#### ADDED — § Política expand/contract

Toda migración que altere un PK o columna con FKs existentes
**SHALL** seguir el patrón:

1. **Expand**: agregar columna nueva (`id_uuid UUID NULL`).
2. **Backfill**: `RunPython` que copia cada fila usando un
   `uuid5(NAMESPACE_URL, f"{table}:{old_id}")` determinístico.
3. **Sync**: la app pasa a leer de la nueva columna (gated por
   setting `USE_NEW_PK_LAYER`).
4. **Contract**: `ALTER TABLE ... ALTER COLUMN id_uuid SET NOT
   NULL`, drop old column.
5. **Reversibilidad**: cada paso tiene su contraparte reversible.

#### ADDED — § Backfill UUID determinístico

Para las tres migraciones existentes, se agrega una migración
`backfill_uuids_for_legacy_pks` (nueva) que:

- Verifica si la columna PK actual es `BigAutoField` (estado pre-migración
  en algún environment) y, si lo es, la backfilea antes del
  `AlterField`.
- Verifica que las FKs que apuntan a esas tablas no apunten a IDs
  que no estén en el conjunto viejo.

### Cambios concretos

1. **Migración nueva** `apps/accounts/migrations/0008_backfill_uuids_customuser_role.py`:
   - `RunPython(backfill_customuser_uuid, reverse_code=noop)` que
     itera sobre `CustomUser` y setea `id` con
     `uuid.uuid5(NAMESPACE_URL, f"customuser:{old_id}")` si `id` es
     int.
   - Idem para `Role`.
   - `state_operations = []` para que esta migración sea
     data-only (Django la detecta como vacía pero ejecuta el
     RunPython).
2. **Migración nueva** `apps/convocatories/migrations/0003_backfill_uuids_convocatory.py`:
   - Idem para `Convocatory`.
3. **Documentación** `docs/migrations/expand-contract.md` (nuevo):
   - Plantilla de migración expand/contract.
   - Tabla de migraciones destructivas existentes y plan de
     remediación.
   - Cómo revertir una migración UUID fallida.
4. **CI guard** `.github/workflows/migrations-safety.yml`:
   - Job que corre `python manage.py makemigrations --check --dry-run`
     y falla si hay migraciones sin backfill que toquen PKs.
5. **Refactor** `apps/accounts/migrations/0006_alter_customuser_id.py`,
   `0007_alter_role_id.py`,
   `apps/convocatories/migrations/0002_alter_convocatory_id.py`:
   agregar comentario en `operations` que referencie la migración
   nueva de backfill y la política de INF-014 (no editar la
   migración histórica — solo anotar).

## Criterios de aceptación

- [ ] Test de la migración nueva: con una base pre-poblada con IDs
      `BigAutoField`, ejecutar la migración y verificar que todos los
      `id` quedan como `UUIDField` con el formato esperado
      (uuid5 determinístico).
- [ ] Test de reversibilidad: ejecutar `migrate accounts 0005` y
      verificar que `id` vuelve a ser int (o que el rollback es
      completo y deja datos consistentes).
- [ ] Test de FKs: las tablas con FKs (`UserRole.role`,
      `Permission.user`, `Solicitud.convocatoria`, etc.) siguen
      resolviendo después del backfill.
- [ ] CI falla si se agrega una migración nueva que altere un PK
      sin un backfill correspondiente.
- [ ] `docs/migrations/expand-contract.md` está commiteado y enlazado
      desde `roadmap.md §4.1 INF-014`.

## Pruebas

- Migración:
  - `apps/accounts/tests/test_migrations_uuid.py` — carga fixtures
    con IDs legacy, aplica la migración, verifica schema y datos.
  - `apps/convocatories/tests/test_migrations_uuid.py` — idem.
- CI:
  - `.github/workflows/migrations-safety.yml` corre en cada PR y
    falla si se introduce una migración destructiva sin backfill.
- Reversibilidad:
  - `pytest -k "test_migrate_back_and_forward"` corre `migrate` en
    ambos sentidos y verifica estado consistente.

## Riesgos y Fuera del alcance

- **Riesgo**: si la base de producción ya migró y los datos están en
  el estado UUID, la nueva migración de backfill no debe romper
  nada. La migración **SHALL** verificar el tipo de columna antes
  de actuar (`if not isinstance(pk, int): return`).
- **Riesgo**: si hay datos inconsistentes entre environments (uno
  migró y otro no), el orden de migraciones puede diverger.
  Mitigación: documentar el estado esperado por environment en
  `docs/migrations/expand-contract.md`.
- **Fuera del alcance**:
  - No se rediseña el modelo de PK (sigue siendo UUID, decisión
    ya tomada).
  - No se cambian otras tablas con PKs int (no estaban en el
    alcance de la auditoría).

## Referencias

- `docs/audits/extended-audit.md` §7, §8.2 AUD-019.
- `roadmap.md` §4.1 INF-014.
- `AGENTS.md` §6 reglas 5 y 9.
