# CHG-804 — Backfill determinístico de UUIDs para Convocatory.
#
# Esta migración es DATA-ONLY (no cambia schema). Se ejecuta después
# de la migración destructiva 0002 (Convocatory) que cambia el PK de
# BigAutoField a UUIDField.
#
# Política expand/contract — ver docs/migrations/expand-contract.md.
#
# Idempotencia: si el PK ya es UUIDField (estado actual del modelo en
# develop/main), la función forward no escribe nada y termina OK.
# Si el PK aún es int (entorno legacy), backfilea con
# uuid5(NAMESPACE_URL, f"convocatory:{old_pk}") y persiste
# update_fields=["id"].
#
# reverse_code es noop intencionalmente. Para escenarios de rollback,
# usar forward-only repair (ver docs/migrations/expand-contract.md).

import uuid

from django.db import migrations


NAMESPACE_URL = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def backfill_convocatory_uuid(apps, schema_editor):
    """Backfill determinístico de Convocatory.pk cuando es int legacy."""
    Convocatory = apps.get_model("convocatories", "Convocatory")
    pk_field = Convocatory._meta.pk
    if pk_field.get_internal_type() == "UUIDField":
        return  # ya migrado: noop idempotente

    for convocatory in Convocatory.objects.all():
        if isinstance(convocatory.pk, uuid.UUID):
            continue
        convocatory.pk = uuid.uuid5(NAMESPACE_URL, f"convocatory:{convocatory.pk}")
        convocatory.save(update_fields=["id"])


def _reverse(apps, schema_editor):
    """Noop documentado.

    Revertir un PK UUID a int requiere una tabla de mapeo
    old_id -> new_id. Sin esa tabla no se puede reconstruir la PK
    original. Para escenarios de rollback, escribir una migración
    forward-only de repair (ver docs/migrations/expand-contract.md).
    """
    return None


class Migration(migrations.Migration):
    dependencies = [
        ("convocatories", "0002_alter_convocatory_id"),
    ]

    operations = [
        migrations.RunPython(backfill_convocatory_uuid, _reverse),
    ]
