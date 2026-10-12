"""Seed the three MunicipioIsla catalog rows for the Archipelago (CHG-506)."""

from django.core.management.base import BaseCommand

from apps.core.models import MunicipioIsla


class Command(BaseCommand):
    help = "Seed the three MunicipioIsla rows (san_andres, providencia, santa_catalina)"

    MUNICIPIOS = [
        {
            "codigo": "san_andres",
            "nombre": "San Andrés",
            "descripcion": "Isla de San Andrés, capital del Archipiélago",
            "orden": 1,
        },
        {
            "codigo": "providencia",
            "nombre": "Providencia",
            "descripcion": "Isla de Providencia y Santa Catalina",
            "orden": 2,
        },
        {
            "codigo": "santa_catalina",
            "nombre": "Santa Catalina",
            "descripcion": "Isla de Santa Catalina, corregimiento de Providencia",
            "orden": 3,
        },
    ]

    def handle(self, *args, **options):
        created_count = 0
        for m in self.MUNICIPIOS:
            municipio, created = MunicipioIsla.objects.get_or_create(
                codigo=m["codigo"],
                defaults={
                    "nombre": m["nombre"],
                    "descripcion": m["descripcion"],
                    "orden": m["orden"],
                    "activo": True,
                },
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Created: {municipio.codigo} — {municipio.nombre}"
                    )
                )
            else:
                self.stdout.write(
                    f"  Exists:  {municipio.codigo} — {municipio.nombre}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ Seed complete: {created_count} created, "
                f"{len(self.MUNICIPIOS) - created_count} existing. "
                f"Total: {MunicipioIsla.objects.count()}"
            )
        )
