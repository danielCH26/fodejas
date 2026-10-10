# Generated for CHG-206 Appeals (2ª instancia)
# Data migration to create R-OFIJUR role idempotently

from django.db import migrations


def create_ofijur_role(apps, schema_editor):
    """Create R-OFIJUR role if it doesn't exist."""
    Role = apps.get_model("accounts", "Role")

    # Create role with get_or_create for idempotency
    role, created = Role.objects.get_or_create(
        code="R-OFIJUR",
        defaults={
            "name": "Oficina Jurídica",
            "type": "interno",
            "description": (
                "Rol para resolver apelaciones en 2ª instancia "
                "ante la Oficina Jurídica de la Gobernación "
                "contra decisiones de la Junta Directiva."
            ),
        },
    )

    if created:
        print(f"[OK] Created role: {role.code} - {role.name}")
    else:
        print(f"[OK] Role already exists: {role.code} - {role.name}")


def reverse_create_ofijur_role(apps, schema_editor):
    """Reverse migration: remove R-OFIJUR role."""
    Role = apps.get_model("accounts", "Role")

    # Only delete if it exists and we created it
    Role.objects.filter(code="R-OFIJUR").delete()
    print("[OK] Removed role: R-OFIJUR")


class Migration(migrations.Migration):

    dependencies = [
        # Depend on the latest accounts migration
        ("accounts", "0005_permission_auth_permission"),
        # Depend on the latest claims migration
        ("claims", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_ofijur_role,
            reverse_create_ofijur_role,
        ),
    ]
