"""Data migration to seed 13 roles from project.md §7."""
from django.db import migrations


def seed_roles(apps, schema_editor):
    """Seed the 13 roles defined in project.md §7."""
    Role = apps.get_model("accounts", "Role")

    roles = [
        {"code": "R-ASPIRANTE", "name": "Aspirante", "type": "externo"},
        {"code": "R-BENEF", "name": "Beneficiario", "type": "externo"},
        {"code": "R-COORD", "name": "Coordinador Técnico FODEJAS", "type": "interno"},
        {"code": "R-CT", "name": "Miembro del Comité Técnico", "type": "interno"},
        {"code": "R-JUNTA", "name": "Miembro de la Junta", "type": "interno"},
        {"code": "R-PRES", "name": "Presidente de la Junta", "type": "interno"},
        {"code": "R-SECEDU", "name": "Secretario de Educación", "type": "interno"},
        {"code": "R-TESOR", "name": "Tesorero General", "type": "interno"},
        {"code": "R-OFIJUR", "name": "Oficina Jurídica", "type": "interno"},
        {"code": "R-CONTROL", "name": "Oficina de Control Interno", "type": "interno"},
        {"code": "R-CIUDA", "name": "Ciudadano", "type": "externo"},
        {"code": "R-ADMIN", "name": "Administrador del sistema", "type": "interno"},
        {"code": "R-AUDITOR", "name": "Auditor externo", "type": "externo"},
    ]

    for role_data in roles:
        Role.objects.get_or_create(
            code=role_data["code"],
            defaults={
                "name": role_data["name"],
                "type": role_data["type"],
            }
        )


def reverse_seed(apps, schema_editor):
    """Remove seeded roles."""
    Role = apps.get_model("accounts", "Role")
    Role.objects.filter(code__startswith="R-").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, reverse_seed),
    ]
