# Política de migraciones — patrón expand/contract

> Documento vivo. Referencia: `roadmap.md §4.1 INF-014`,
> `AGENTS.md §6 reglas 5 y 9`, y la auditoría
> `docs/audits/extended-audit.md §7, §8.2 AUD-019`.

## Por qué expand/contract

Un deploy con cero indisponibilidad exige que **ningún paso de una
migración pueda romper las foreign keys existentes** ni dejar la tabla
en un estado que la capa de aplicación no pueda leer. Una migración que
altera el tipo de PK de `BigAutoField` a `UUIDField` (o cualquier
re-casteo sobre una columna con FKs activas) **no cumple esa promesa**:
`ALTER TABLE ... ALTER COLUMN id TYPE UUID USING ...` requiere un cast
explícito y, si hay filas, falla o reescribe en cascada las columnas
FK que la apuntan.

`roadmap.md §4.1 INF-014` establece la política expand/contract como
la forma correcta de aplicar cambios estructurales con cero downtime y
trazabilidad completa.

## Receta en 4 pasos

1. **Expand** — agregar la columna nueva como nullable, sin tocar la
   columna original.
   - Django: `migrations.AddField(model_name=..., name='id_uuid',
     field=models.UUIDField(null=True, blank=True))`.
   - PostgreSQL: `ALTER TABLE ... ADD COLUMN id_uuid UUID NULL;`.
2. **Backfill** — `migrations.RunPython` que itera filas y rellena la
   nueva columna de forma determinística.
   - Para conversiones a UUID: `uuid.uuid5(NAMESPACE_URL,
     f"{table}:{old_pk}")`.
   - La función **debe** ser idempotente y **debe** verificar el tipo
     actual de la columna antes de actuar.
3. **Swap** — la capa de aplicación pasa a leer la nueva columna
   (gated por setting/feature flag), y el schema hace `SET NOT NULL` +
   constraints FK sobre la nueva columna.
4. **Contract** — `migrations.RemoveField` sobre la columna original,
   sólo cuando los readers están migrados y no quedan queries
   referenciándola.

Cada paso es una migración independiente para que el grafo de
dependencias Django refleje el orden real y permita rollback
quirúrgico.

## Plantilla de migración (data-only backfill)

```python
"""Backfill determinístico de UUIDs para <Tabla>.

Política expand/contract — ver docs/migrations/expand-contract.md.
Idempotente: si el PK ya es UUIDField, noop.
"""
import uuid

from django.db import migrations

NAMESPACE_URL = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def backfill_<tabla>_uuid(apps, schema_editor):
    Model = apps.get_model("<app>", "<Modelo>")
    if Model._meta.pk.get_internal_type() == "UUIDField":
        return  # ya migrado
    for row in Model.objects.all():
        if isinstance(row.pk, uuid.UUID):
            continue
        row.pk = uuid.uuid5(NAMESPACE_URL, f"<tabla>:{row.pk}")
        row.save(update_fields=["id"])


def _reverse(apps, schema_editor):
    """Noop documentado: sin tabla de mapeo no se puede revertir."""
    return None


class Migration(migrations.Migration):
    dependencies = [("<app>", "<nnnn_prev>")]
    operations = [migrations.RunPython(backfill_<tabla>_uuid, _reverse)]
```

## Ejemplo guiado: `accounts.CustomUser`

1. **Expand** — `0006_alter_customuser_id.py` (histórico 2026-07-17,
   schema-only `AlterField`).
2. **Backfill** — `0008_backfill_uuids_customuser_role.py` (CHG-804,
   data-only `RunPython`). Itera `CustomUser.objects.all()` y aplica
   `uuid.uuid5(NAMESPACE_URL, f"customuser:{old_pk}")` a filas con PK
   entero.
3. **Swap** — la app ya lee `id` desde el primer deploy post-0006
   (Django ORM usa el tipo declarado en el modelo, no el de la
   columna).
4. **Contract** — fuera del alcance de CHG-804; no aplica porque la
   columna `id` original no existe en el modelo actual (ya fue
   redefinida como `UUIDField`).

## Historia de migraciones destructivas

| # | Migración | Fecha | Tabla | PK origen | PK destino | Riesgo original | Mitigación CHG-804 |
|---|-----------|-------|-------|-----------|------------|-----------------|---------------------|
| 1 | `accounts/migrations/0006_alter_customuser_id.py` | 2026-07-17 | `accounts_customuser` | `BigAutoField` | `UUIDField` | Cast en cascada sobre FKs | `0008_backfill_uuids_customuser_role.py` re-asigna IDs determinísticamente antes de que las filas queden con PK inválido |
| 2 | `accounts/migrations/0007_alter_role_id.py` | 2026-07-18 | `accounts_role` | `BigAutoField` | `UUIDField` | Mismo | Misma migración 0008 (backfill combinado) |
| 3 | `convocatories/migrations/0002_alter_convocatory_id.py` | 2026-07-18 | `convocatories_convocatory` | `BigAutoField` | `UUIDField` | Mismo | `0003_backfill_uuids_convocatory.py` |

Estas tres migraciones históricas quedan **anotadas** con un comentario
al tope del archivo que referencia la nueva política y la migración de
backfill correspondiente. **No se modifica** `operations` ni
`dependencies` — el historial de migraciones Django es inmutable.

## Cómo revertir una migración UUID fallida

**Regla**: no se hace `migrate accounts 0006` para volver al PK entero.
Esa operación es destructiva (pierde la PK UUID actual).

**Forward-only repair**:

1. Crear una nueva migración `0009_repair_uuid_namespace.py`.
2. Sustituir el namespace `NAMESPACE_URL` por uno nuevo (por ejemplo
   el UUID del incident ticket) y volver a calcular:
   `new_id = uuid.uuid5(NEW_NAMESPACE, f"{table}:{current_pk}")`.
3. Reasignar `pk` con `save(update_fields=["id"])` y dejar que Django
   propague a las FKs en cascada.
4. Documentar en `apps/audit/` como evento de remediación.

Esta estrategia preserva el contrato de irreversibilidad controlada y
deja un rastro auditable.

## Estado esperado por environment

| Environment | Estado del PK al deploy de CHG-804 | Acción de la migración 0008/0003 |
|-------------|-------------------------------------|-----------------------------------|
| dev | Ya es `UUIDField` (modelo actual) | Noop |
| staging | Idem | Noop |
| production | Idem | Noop |
| environment legacy no migrado | `BigAutoField` | Backfill completo + chain a 0006/0007/0002 |

## Enlaces

- `roadmap.md §4.1 INF-014` — origen de la política.
- `docs/audits/extended-audit.md §7, §8.2 AUD-019` — hallazgo crítico
  que disparó CHG-804.
- `.github/workflows/migrations-safety.yml` — guard automático para
  prevenir regresiones.
