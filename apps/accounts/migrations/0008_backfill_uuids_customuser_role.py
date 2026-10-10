# CHG-804 — Backfill determinístico de UUIDs para CustomUser y Role.
#
# Esta migración es DATA-ONLY (no cambia schema). Se ejecuta después
# de las migraciones destructivas 0006 (CustomUser) y 0007 (Role) que
# cambian el PK de BigAutoField a UUIDField.
#
# Política expand/contract — ver docs/migrations/expand-contract.md.
#
# Idempotencia: si el PK ya es UUIDField (estado actual del modelo en
# develop/main), la función forward no escribe nada y termina OK.
# Si el PK aún es int (entorno legacy), backfilea con
# uuid5(NAMESPACE_URL, f"{table}:{old_pk}") y persiste update_fields=["id"].
#
# reverse_code es noop intencionalmente: revertir un cambio de PK a su
# tipo anterior sin una tabla de mapeo old_id -> new_id es destructivo.
# Para "deshacer" una migración UUID fallida, usar forward-only repair
# (ver docs/migrations/expand-contract.md §"Cómo revertir").

import uuid

from django.db import migrations

NAMESPACE_URL = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")


def backfill_customuser_uuid(apps, schema_editor):
    """Backfill determinístico de CustomUser.pk cuando es int legacy."""
    CustomUser = apps.get_model("accounts", "CustomUser")
    pk_field = CustomUser._meta.pk
    if pk_field.get_internal_type() == "UUIDField":
        return  # ya migrado: noop idempotente

    for user in CustomUser.objects.all():
        if isinstance(user.pk, uuid.UUID):
            continue
        user.pk = uuid.uuid5(NAMESPACE_URL, f"customuser:{user.pk}")
        user.save(update_fields=["id"])


def backfill_role_uuid(apps, schema_editor):
    """Backfill determinístico de Role.pk cuando es int legacy."""
    Role = apps.get_model("accounts", "Role")
    pk_field = Role._meta.pk
    if pk_field.get_internal_type() == "UUIDField":
        return  # ya migrado: noop idempotente

    for role in Role.objects.all():
        if isinstance(role.pk, uuid.UUID):
            continue
        role.pk = uuid.uuid5(NAMESPACE_URL, f"role:{role.pk}")
        role.save(update_fields=["id"])


def _forward(apps, schema_editor):
    backfill_customuser_uuid(apps, schema_editor)
    backfill_role_uuid(apps, schema_editor)


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
        ("accounts", "0007_alter_role_id"),
    ]

    operations = [
        migrations.RunPython(_forward, _reverse),
    ]
