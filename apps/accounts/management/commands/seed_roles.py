"""
Command to seed roles into the database.
"""

from django.core.management.base import BaseCommand

from apps.accounts.models import Role


class Command(BaseCommand):
    help = "Seed roles into the database"

    ROLES = [
        {
            "code": "R-ADMIN",
            "name": "Administrador del sistema",
            "type": "interno",
            "description": "Gestión de usuarios, roles, catálogos, configuración global.",
        },
        {
            "code": "R-COORD",
            "name": "Coordinador Técnico FODEJAS",
            "type": "interno",
            "description": "Opera el día a día. Crea convocatorias, valida requisitos, propone adjudicaciones, sigue beneficiarios.",
        },
        {
            "code": "R-CT",
            "name": "Miembro del Comité Técnico",
            "type": "interno",
            "description": "Emite conceptos técnicos, evalúa postulaciones, propone priorización.",
        },
        {
            "code": "R-JUNTA",
            "name": "Miembro de la Junta",
            "type": "interno",
            "description": "Aprueba listados, presupuesto, reglamento, sanciones.",
        },
        {
            "code": "R-PRES",
            "name": "Presidente de la Junta",
            "type": "interno",
            "description": "Firma autorizaciones de pago y preside sesiones.",
        },
        {
            "code": "R-SECEDU",
            "name": "Secretario de Educación",
            "type": "interno",
            "description": "Ordenador del gasto delegado. Firma resoluciones y actos administrativos.",
        },
        {
            "code": "R-TESOR",
            "name": "Tesorero General",
            "type": "interno",
            "description": "Ejecuta los pagos desde sus sistemas bancarios.",
        },
        {
            "code": "R-OFIJUR",
            "name": "Oficina Jurídica",
            "type": "interno",
            "description": "Resuelve apelaciones (2ª instancia) y conceptúa actos administrativos.",
        },
        {
            "code": "R-CONTROL",
            "name": "Oficina de Control Interno",
            "type": "interno",
            "description": "Auditoría, veedurías, investigaciones disciplinarias internas.",
        },
        {
            "code": "R-AUDITOR",
            "name": "Auditor externo / Ente de control",
            "type": "externo",
            "description": "Acceso de solo lectura a bitácora, reportes y datos para fines de fiscalización.",
        },
        {
            "code": "R-ASPIRANTE",
            "name": "Aspirante",
            "type": "externo",
            "description": "Persona que se inscribe a una convocatoria. Acceso solo a su perfil y sus postulaciones.",
        },
        {
            "code": "R-BENEF",
            "name": "Beneficiario",
            "type": "externo",
            "description": "Aspirante seleccionado con acto administrativo en firme. Acceso a reportes, condonación y obligaciones.",
        },
        {
            "code": "R-CIUDA",
            "name": "Ciudadano (portal público)",
            "type": "externo",
            "description": "Acceso a datos abiertos y portal de transparencia (sin autenticación profunda).",
        },
    ]

    def handle(self, *args, **options):
        created_count = 0
        for role_data in self.ROLES:
            role, created = Role.objects.get_or_create(
                code=role_data["code"],
                defaults={
                    "name": role_data["name"],
                    "type": role_data["type"],
                    "description": role_data["description"],
                },
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created role: {role.code} - {role.name}"))
            else:
                self.stdout.write(f"  Role exists: {role.code}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Created {created_count} new roles. Total roles: {Role.objects.count()}"
            )
        )
