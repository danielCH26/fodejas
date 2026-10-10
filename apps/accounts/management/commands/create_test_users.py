"""
Command to create test users for each role in the system.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from apps.accounts.models import Role, UserRole

User = get_user_model()

# Password used for all test users (following project conventions)
TEST_PASSWORD = "Test123456!"

# Mapping of roles to test users
TEST_USERS = [
    {
        "email": "admin@fodejas.test",
        "documento": "1111111",
        "first_name": "Administrador",
        "last_name": "Sistema",
        "roles": ["R-ADMIN"],
    },
    {
        "email": "coord@fodejas.test",
        "documento": "2222222",
        "first_name": "Coordinador",
        "last_name": "Técnico",
        "roles": ["R-COORD"],
    },
    {
        "email": "ct@fodejas.test",
        "documento": "3333333",
        "first_name": "Comité",
        "last_name": "Técnico",
        "roles": ["R-CT"],
    },
    {
        "email": "junta@fodejas.test",
        "documento": "4444444",
        "first_name": "Miembro",
        "last_name": "Junta",
        "roles": ["R-JUNTA"],
    },
    {
        "email": "pres@fodejas.test",
        "documento": "5555555",
        "first_name": "Presidente",
        "last_name": "Junta",
        "roles": ["R-PRES"],
    },
    {
        "email": "secedu@fodejas.test",
        "documento": "6666666",
        "first_name": "Secretario",
        "last_name": "Educación",
        "roles": ["R-SECEDU"],
    },
    {
        "email": "tesorero@fodejas.test",
        "documento": "7777777",
        "first_name": "Tesorero",
        "last_name": "General",
        "roles": ["R-TESOR"],
    },
    {
        "email": "ofijur@fodejas.test",
        "documento": "8888888",
        "first_name": "Oficina",
        "last_name": "Jurídica",
        "roles": ["R-OFIJUR"],
    },
    {
        "email": "control@fodejas.test",
        "documento": "9999999",
        "first_name": "Control",
        "last_name": "Interno",
        "roles": ["R-CONTROL"],
    },
    {
        "email": "auditor@fodejas.test",
        "documento": "1010101",
        "first_name": "Auditor",
        "last_name": "Externo",
        "roles": ["R-AUDITOR"],
    },
    {
        "email": "aspirante@fodejas.test",
        "documento": "1212121",
        "first_name": "Aspirante",
        "last_name": "Prueba",
        "roles": ["R-ASPIRANTE"],
    },
    {
        "email": "beneficiario@fodejas.test",
        "documento": "1313131",
        "first_name": "Beneficiario",
        "last_name": "Prueba",
        "roles": ["R-BENEF"],
    },
    {
        "email": "ciudadano@fodejas.test",
        "documento": "1414141",
        "first_name": "Ciudadano",
        "last_name": "Prueba",
        "roles": ["R-CIUDA"],
    },
]


class Command(BaseCommand):
    help = "Create test users for each role in the system"

    def handle(self, *args, **options):
        # Ensure all roles exist
        self.stdout.write("Checking roles...")
        role_codes = [user["roles"][0] for user in TEST_USERS]
        existing_roles = set(Role.objects.values_list("code", flat=True))

        for code in role_codes:
            if code not in existing_roles:
                self.stdout.write(self.style.WARNING(f"  Role {code} not found in database!"))

        # Create users
        created_count = 0
        for user_data in TEST_USERS:
            email = user_data["email"]
            role_codes = user_data["roles"]

            # Check if user already exists
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "documento": user_data["documento"],
                    "first_name": user_data["first_name"],
                    "last_name": user_data["last_name"],
                },
            )

            # Set password if created or not set
            if created:
                user.set_password(TEST_PASSWORD)
                user.save()
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  Created user: {email}"))
            else:
                self.stdout.write(f"  User exists: {email}")

            # Assign roles
            for role_code in role_codes:
                role = Role.objects.filter(code=role_code).first()
                if not role:
                    self.stdout.write(
                        self.style.ERROR(f"    Role {role_code} not found - skipping!")
                    )
                    continue

                user_role, ur_created = UserRole.objects.get_or_create(
                    user=user, role=role, defaults={"convocation_scope_id": None}
                )

                if ur_created:
                    self.stdout.write(self.style.SUCCESS(f"    Assigned role: {role_code}"))
                else:
                    self.stdout.write(f"    Role already assigned: {role_code}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Created {created_count} new users. "
                f"All users have password: {TEST_PASSWORD}"
            )
        )

        # Print summary table
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("TEST USERS SUMMARY")
        self.stdout.write("=" * 70)
        self.stdout.write(f"{'Email':<30} {'Documento':<12} {'Rol':<15}")
        self.stdout.write("-" * 70)
        for user_data in TEST_USERS:
            self.stdout.write(
                f"{user_data['email']:<30} "
                f"{user_data['documento']:<12} "
                f"{user_data['roles'][0]:<15}"
            )
        self.stdout.write("-" * 70)
        self.stdout.write(f"Password para todos: {TEST_PASSWORD}")
        self.stdout.write("=" * 70)
