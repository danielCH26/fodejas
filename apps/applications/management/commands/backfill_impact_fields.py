"""Backfill ies_nombre and municipio_origen on Solicitud from JSON blobs (CHG-506).

Idempotent: writes only when destination value differs from current.
Supports --dry-run to emit report without writes.
"""

import re

from django.core.management.base import BaseCommand

from apps.applications.models import Solicitud
from apps.core.models import MunicipioIsla


class Command(BaseCommand):
    help = "Backfill ies_nombre and municipio_origen on Solicitud from JSON blobs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Compute report only; do not write to the database",
        )

    def _normalize_ies(self, value):
        """Strip whitespace and collapse multiple spaces (CHG-506 §2.1)."""
        if not value:
            return None
        return re.sub(r" {2,}", " ", str(value).strip())

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # Load catalog ONCE — dict keyed by codigo.casefold() and nombre.casefold()
        municipio_by_codigo = {
            m.codigo.casefold(): m
            for m in MunicipioIsla.objects.all()
        }
        municipio_by_nombre = {
            m.nombre.casefold(): m
            for m in MunicipioIsla.objects.all()
        }

        counters = {
            "processed": 0,
            "ies_updated": 0,
            "ies_unchanged": 0,
            "ies_missing_data": 0,
            "municipio_matched": 0,
            "municipio_unmatched": 0,
            "municipio_missing_data": 0,
        }
        unmatched_raw = set()

        queryset = Solicitud.objects.all().iterator(chunk_size=500)

        for solicitud in queryset:
            counters["processed"] += 1
            updated_ies = False
            updated_municipio = False

            # --- ies_nombre ---
            datos_academicos = solicitud.datos_academicos
            raw_ies = None
            if isinstance(datos_academicos, dict):
                raw_ies = datos_academicos.get("institucion")

            if raw_ies is not None:
                normalized_ies = self._normalize_ies(raw_ies)
                current = solicitud.ies_nombre or ""
                if current != normalized_ies:
                    if not dry_run:
                        solicitud.ies_nombre = normalized_ies
                        updated_ies = True
                    counters["ies_updated"] += 1
                else:
                    counters["ies_unchanged"] += 1
            else:
                counters["ies_missing_data"] += 1

            # --- municipio_origen ---
            datos_personales = solicitud.datos_personales
            raw_municipio = None
            if isinstance(datos_personales, dict):
                raw_municipio = datos_personales.get("municipio")

            if raw_municipio is not None:
                # Primary: match codigo.casefold()
                match = municipio_by_codigo.get(raw_municipio.casefold())
                # Fallback: match nombre.casefold()
                if match is None:
                    match = municipio_by_nombre.get(raw_municipio.casefold())

                current_fk_id = (
                    solicitud.municipio_origen_id
                    if solicitud.municipio_origen_id is not None
                    else None
                )
                match_id = match.id if match else None

                if match is not None and current_fk_id != match_id:
                    if not dry_run:
                        solicitud.municipio_origen = match
                        updated_municipio = True
                    counters["municipio_matched"] += 1
                elif match is not None:
                    counters["municipio_matched"] += 1
                else:
                    # No match: assign null only if currently non-null (idempotent)
                    if current_fk_id is not None:
                        if not dry_run:
                            solicitud.municipio_origen = None
                            updated_municipio = True
                    counters["municipio_unmatched"] += 1
                    unmatched_raw.add(str(raw_municipio))
            else:
                counters["municipio_missing_data"] += 1

            # Write only if something changed and not dry run
            if not dry_run and (updated_ies or updated_municipio):
                # Use update() for efficiency — only save changed fields
                update_kwargs = {}
                if updated_ies:
                    update_kwargs["ies_nombre"] = solicitud.ies_nombre
                if updated_municipio:
                    update_kwargs["municipio_origen_id"] = (
                        solicitud.municipio_origen_id
                    )
                Solicitud.objects.filter(pk=solicitud.pk).update(**update_kwargs)

        # --- Report ---
        self.stdout.write(f"\n{'[DRY RUN] ' if dry_run else ''}Backfill report:")
        self.stdout.write(f"  processed:            {counters['processed']}")
        self.stdout.write(f"  ies_updated:          {counters['ies_updated']}")
        self.stdout.write(f"  ies_unchanged:        {counters['ies_unchanged']}")
        self.stdout.write(f"  ies_missing_data:      {counters['ies_missing_data']}")
        self.stdout.write(f"  municipio_matched:    {counters['municipio_matched']}")
        self.stdout.write(f"  municipio_unmatched:  {counters['municipio_unmatched']}")
        if unmatched_raw:
            self.stdout.write(
                self.style.WARNING(
                    f"    (unmatched municipio values seen: {sorted(unmatched_raw)})"
                )
            )
        self.stdout.write(
            f"  municipio_missing_data: {counters['municipio_missing_data']}"
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\n  --dry-run: no database writes performed."
                )
            )
        else:
            writes = counters["ies_updated"]
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✓ Done. {writes} row(s) written."
                )
            )
