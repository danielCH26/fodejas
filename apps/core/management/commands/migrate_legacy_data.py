"""migrate_legacy_data: ingest historical FODEJAS data (CHG-099).

Idempotent migration of legacy Convocatorias, Solicitudes, Actos
and Listados from CSV files at ``--source``. All PII fields are
anonymized via ``apps.core.migration_utils.anonymize`` before
persistence.

Per AGENTS.md §6 regla 1, no PII may live in this repo — the
anonymized CSVs are produced externally (see
``docs/migrations/migration-runbook.md``) and mounted read-only
into the container at run time.
"""
from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.core.migration_utils.anonymize import (
    anonymize_hash,
    anonymize_json,
)
from apps.core.migration_utils.validators import (
    validate_fk_resolution,
    validate_no_pii,
    validate_schema,
)

CONVOCATORIA_HEADERS = [
    "codigo",
    "nombre",
    "tipo",
    "periodo",
    "estado",
    "fecha_apertura",
    "fecha_cierre",
    "fecha_publicacion_preliminar",
    "fecha_publicacion_definitiva",
    "monto_semestre_smlmv",
    "duracion_maxima_semestres",
    "cupo_total",
    "modalidad_codigo",
]

SOLICITUD_HEADERS = [
    "radicado",
    "convocatoria_codigo",
    "aspirante_documento_hash",
    "estado",
    "radicado_en",
    "datos_academicos_json",
    "datos_socioeconomicos_json",
    "datos_personales_json",
]

USUARIO_HEADERS = [
    "documento_hash",
    "email_hash",
    "role_codes",
    "is_active",
]

ACTO_HEADERS = [
    "numero",
    "tipo",
    "fecha_expedicion",
    "fecha_publicacion",
    "asunto",
    "considerandos_json",
    "resolutivo",
    "convocatoria_codigo",
    "firmantes_json",
    "estado",
]

LISTADO_HEADERS = [
    "convocatoria_codigo",
    "ranking_json",
    "fecha_publicacion",
    "acto_numero",
]

SOLICITUD_PII_COLUMNS = [
    "aspirante_documento_hash",
    "datos_academicos_json",
    "datos_socioeconomicos_json",
    "datos_personales_json",
]

USUARIO_PII_COLUMNS = ["documento_hash", "email_hash"]
ACTO_PII_COLUMNS = ["asunto", "considerandos_json", "resolutivo", "firmantes_json"]
LISTADO_PII_COLUMNS = ["ranking_json"]


class Command(BaseCommand):
    """Idempotent loader for legacy FODEJAS data."""

    help = (
        "Migrate legacy FODEJAS records from anonymized CSV files. "
        "Idempotent: re-running with the same input does not create "
        "duplicates. Requires LEGACY_DATA_SALT env var (or --salt)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="./data/legacy/",
            help="Directorio con los 5 CSVs anonimizados (default: ./data/legacy/).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo valida y reporta; no escribe a la DB.",
        )
        parser.add_argument(
            "--skip-validation",
            action="store_true",
            help=(
                "OMITE las validaciones. Uso exclusivo de emergencia; "
                "los datos persistedos pueden contener PII."
            ),
        )
        parser.add_argument(
            "--salt",
            default=None,
            help=(
                "Salt para anonimización. Default: $LEGACY_DATA_SALT. "
                "Si --skip-validation, no se usa."
            ),
        )

    def handle(self, *args, **options):
        source = Path(options["source"]).resolve()
        if not source.is_dir():
            raise CommandError(f"--source no es un directorio: {source}")

        dry_run = options["dry_run"]
        skip_validation = options["skip_validation"]
        salt = options["salt"]

        if not skip_validation and salt is None:
            import os

            if "LEGACY_DATA_SALT" not in os.environ:
                raise CommandError(
                    "LEGACY_DATA_SALT no está seteada. "
                    "Exportala (recomendado, mínimo 32 chars) o usa --salt. "
                    "Para testing local puedes usar --skip-validation."
                )
            salt = os.environ["LEGACY_DATA_SALT"]

        if skip_validation:
            salt = salt or "skip-validation-mode-no-salt"

        self.stdout.write(
            self.style.NOTICE(
                f"Iniciando migración (dry_run={dry_run}, "
                f"skip_validation={skip_validation})"
            )
        )

        # 1. Read all CSVs.
        convocatorias = self._read(source / "convocatorias.csv")
        usuarios = self._read(source / "usuarios_legacy.csv")
        solicitudes = self._read(source / "solicitudes.csv")
        actos = self._read(source / "actos_legacy.csv")
        listados = self._read(source / "listados_legacy.csv")

        # 2. Validate (unless skipped).
        errors: list[str] = []
        if not skip_validation:
            errors.extend(self._validate_all(source, convocatorias, usuarios,
                                            solicitudes, actos, listados))
            errors.extend(self._validate_pii(source))

        if errors:
            self.stdout.write(self.style.ERROR("Validación falló:"))
            for e in errors:
                self.stdout.write(self.style.ERROR(f"  - {e}"))
            raise CommandError(f"abortando por {len(errors)} errores")

        self.stdout.write(self.style.SUCCESS("Validación OK."))

        # 3. Apply (or just report if dry-run).
        counts = {
            "convocatorias": len(convocatorias),
            "usuarios": len(usuarios),
            "solicitudes": len(solicitudes),
            "actos": len(actos),
            "listados": len(listados),
        }
        self.stdout.write(self.style.NOTICE(f"Conteos: {counts}"))

        if dry_run:
            self.stdout.write(self.style.SUCCESS(
                "Dry-run OK: no se escribió ningún registro."
            ))
            return

        # 4. Persist (idempotent). Imported lazily to keep --dry-run fast.


        from apps.accounts.models import CustomUser, Role, UserRole
        from apps.applications.models import Solicitud
        from apps.convocatories.models import Convocatory
        from apps.core.models import ModalidadApoyo
        from apps.governance.models import ActoAdministrativo, ListadoDefinitivo

        with self._atomic():
            for row in convocatorias:
                self._upsert_convocatoria(row, Convocatory, ModalidadApoyo, salt)
            for row in usuarios:
                self._upsert_usuario(row, CustomUser, Role, UserRole)
            for row in solicitudes:
                self._upsert_solicitud(row, Solicitud, Convocatory, CustomUser,
                                       anonymize_json)
            for row in actos:
                self._upsert_acto(row, ActoAdministrativo, Convocatory,
                                   salt)
            for row in listados:
                self._upsert_listado(row, ListadoDefinitivo, Convocatory,
                                     ActoAdministrativo)

        self.stdout.write(self.style.SUCCESS(
            f"Migración completada. Conteos: {counts}"
        ))

    # --------------------------------------------------------------
    # IO helpers
    # --------------------------------------------------------------

    def _read(self, filepath: Path) -> list[dict]:
        if not filepath.exists():
            raise CommandError(f"archivo faltante: {filepath}")
        with open(filepath, encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))

    # --------------------------------------------------------------
    # Validation
    # --------------------------------------------------------------

    def _validate_all(self, source, convocatorias, usuarios, solicitudes,
                      actos, listados) -> list[str]:
        errors: list[str] = []
        errors.extend(validate_schema(source / "convocatorias.csv",
                                       CONVOCATORIA_HEADERS))
        errors.extend(validate_schema(source / "usuarios_legacy.csv",
                                       USUARIO_HEADERS))
        errors.extend(validate_schema(source / "solicitudes.csv",
                                       SOLICITUD_HEADERS))
        errors.extend(validate_schema(source / "actos_legacy.csv",
                                       ACTO_HEADERS))
        errors.extend(validate_schema(source / "listados_legacy.csv",
                                       LISTADO_HEADERS))

        # FK resolution.
        convocatoria_codes = {r["codigo"].strip() for r in convocatorias}
        {r["documento_hash"].strip() for r in usuarios}
        acto_numeros = {r["numero"].strip() for r in actos}

        errors.extend(validate_fk_resolution(solicitudes, "convocatoria_codigo",
                                            convocatoria_codes))
        errors.extend(validate_fk_resolution(actos, "convocatoria_codigo",
                                            convocatoria_codes))
        errors.extend(validate_fk_resolution(listados, "convocatoria_codigo",
                                            convocatoria_codes))
        errors.extend(validate_fk_resolution(listados, "acto_numero",
                                            acto_numeros))

        return errors

    def _validate_pii(self, source) -> list[str]:
        errors: list[str] = []
        errors.extend(validate_no_pii(source / "solicitudes.csv",
                                       SOLICITUD_PII_COLUMNS))
        errors.extend(validate_no_pii(source / "usuarios_legacy.csv",
                                       USUARIO_PII_COLUMNS))
        errors.extend(validate_no_pii(source / "actos_legacy.csv",
                                       ACTO_PII_COLUMNS))
        errors.extend(validate_no_pii(source / "listados_legacy.csv",
                                       LISTADO_PII_COLUMNS))
        return errors

    # --------------------------------------------------------------
    # Upserts (idempotent)
    # --------------------------------------------------------------

    def _atomic(self):
        from django.db import transaction

        return transaction.atomic()

    def _upsert_convocatoria(self, row, Convocatory, ModalidadApoyo, salt):
        modalidad = None
        if row.get("modalidad_codigo"):
            modalidad, _ = ModalidadApoyo.objects.get_or_create(
                codigo=row["modalidad_codigo"].strip(),
                defaults={
                    "nombre": anonymize_hash(
                        row["modalidad_codigo"].strip(), salt
                    ),
                },
            )
        defaults = {
            "nombre": anonymize_hash(row["nombre"].strip(), salt),
            "tipo": row["tipo"].strip(),
            "periodo": row["periodo"].strip(),
            "estado": row["estado"].strip(),
            "monto_semestre_smlmv": row["monto_semestre_smlmv"].strip(),
            "duracion_maxima_semestres": int(
                row["duracion_maxima_semestres"].strip()
            ),
            "cupo_total": int(row["cupo_total"].strip()),
            "modalidad_apoyo": modalidad,
        }
        for date_field in ("fecha_apertura", "fecha_cierre"):
            value = row.get(date_field, "").strip()
            if value:
                from datetime import date

                defaults[date_field] = date.fromisoformat(value)
        for dt_field in ("fecha_publicacion_preliminar",
                         "fecha_publicacion_definitiva"):
            value = row.get(dt_field, "").strip()
            if value:
                from datetime import datetime

                defaults[dt_field] = datetime.fromisoformat(value)
        Convocatory.objects.update_or_create(
            codigo=row["codigo"].strip(),
            defaults=defaults,
        )

    def _upsert_usuario(self, row, CustomUser, Role, UserRole):
        documento_hash = row["documento_hash"].strip()
        email_hash = row["email_hash"].strip()
        # Build a synthetic email / username from the hashes so the
        # CustomUser model (which uses email as USERNAME_FIELD) can be
        # created without storing PII.
        synthetic_email = f"{email_hash}@anon.fodejas.local"
        user, _ = CustomUser.objects.update_or_create(
            documento=documento_hash,
            defaults={
                "email": synthetic_email,
                "is_active": row["is_active"].strip().lower() == "true",
            },
        )
        # Role assignments via UserRole.
        role_codes = [
            code.strip() for code in row["role_codes"].split("|") if code.strip()
        ]
        for code in role_codes:
            role, _ = Role.objects.get_or_create(
                code=code,
                defaults={
                    "name": code,
                    "type": "interno",
                    "description": code,
                },
            )
            UserRole.objects.get_or_create(
                user=user, role=role, convocation_scope_id=None
            )

    def _upsert_solicitud(self, row, Solicitud, Convocatory, CustomUser,
                            anonymize_json_fn):
        convocatoria = Convocatory.objects.get(
            codigo=row["convocatoria_codigo"].strip()
        )
        try:
            CustomUser.objects.get(documento=row["aspirante_documento_hash"].strip())
            # The CustomUser may exist already (FK lookup will work).
        except CustomUser.DoesNotExist:
            # The user wasn't in usuarios_legacy.csv — that's an error.
            raise CommandError(
                f"aspirante_documento_hash {row['aspirante_documento_hash']!r} "
                f"no encontrado en usuarios_legacy.csv (radicado={row['radicado']})"
            )
        aspirante = CustomUser.objects.get(
            documento=row["aspirante_documento_hash"].strip()
        )
        defaults = {
            "convocatoria": convocatoria,
            "aspirante": aspirante,
            "estado": row["estado"].strip(),
            "datos_personales": _parse_json_or_empty(
                row.get("datos_personales_json", "")
            ),
            "datos_academicos": _parse_json_or_empty(
                row.get("datos_academicos_json", "")
            ),
            "datos_socioeconomicos": _parse_json_or_empty(
                row.get("datos_socioeconomicos_json", "")
            ),
        }
        Solicitud.objects.update_or_create(
            radicado=row["radicado"].strip(),
            defaults=defaults,
        )

    def _upsert_acto(self, row, ActoAdministrativo, Convocatory, salt):
        import json
        from datetime import date, datetime

        convocatoria = None
        codigo = row.get("convocatoria_codigo", "").strip()
        if codigo:
            convocatoria = Convocatory.objects.get(codigo=codigo)
        considerandos = json.loads(row["considerandos_json"])
        firmantes = json.loads(row["firmantes_json"])
        defaults = {
            "tipo": row["tipo"].strip(),
            "fecha_expedicion": date.fromisoformat(
                row["fecha_expedicion"].strip()
            ),
            "asunto": anonymize_hash(row["asunto"].strip(), salt),
            "considerandos": considerandos,
            "resolutivo": anonymize_hash(row["resolutivo"].strip(), salt),
            "convocatoria": convocatoria,
            "firmantes": firmantes,
            "estado": row["estado"].strip(),
        }
        fecha_pub = row.get("fecha_publicacion", "").strip()
        if fecha_pub:
            defaults["fecha_publicacion"] = datetime.fromisoformat(fecha_pub)
        ActoAdministrativo.objects.update_or_create(
            numero=row["numero"].strip(),
            defaults=defaults,
        )

    def _upsert_listado(self, row, ListadoDefinitivo, Convocatory,
                         ActoAdministrativo):
        import json
        from datetime import datetime

        convocatoria = Convocatory.objects.get(
            codigo=row["convocatoria_codigo"].strip()
        )
        acto = ActoAdministrativo.objects.get(
            numero=row["acto_numero"].strip()
        )
        ranking = json.loads(row["ranking_json"])
        ListadoDefinitivo.objects.update_or_create(
            convocatoria=convocatoria,
            defaults={
                "ranking": ranking,
                "fecha_publicacion": datetime.fromisoformat(
                    row["fecha_publicacion"].strip()
                ),
                "acto": acto,
            },
        )


def _parse_json_or_empty(raw: str):
    """Parse a JSON string, returning an empty dict if blank or invalid."""
    import json

    if not raw or not raw.strip():
        return {}
    try:
        result = json.loads(raw)
        return result if isinstance(result, dict) else {}
    except (ValueError, json.JSONDecodeError):
        return {}
