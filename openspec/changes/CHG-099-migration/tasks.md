# Tasks — CHG-099 Migración de datos previos

> Referencia: `proposal.md`. Plantilla según `AGENTS.md §4`.

## 1. Documentación de schemas

- [ ] Crear `docs/migrations/data-schemas.md` con la tabla de los 5
      archivos CSV esperados (convocatorias, solicitudes, usuarios
      legacy, actos legacy, listados legacy). Cada archivo lista
      columnas, tipo, nullability, y nota de anonimización si
      aplica.
- [ ] Crear `docs/migrations/migration-runbook.md` con el
      procedimiento paso a paso: 1) recibir archivos del operador,
      2) anonimizar fuera del repo, 3) montar volumen read-only,
      4) ejecutar `--dry-run`, 5) revisar reporte, 6) ejecutar
      `--apply`, 7) auditar. Checklist de anonimización al final.

## 2. Anonimización

- [ ] Crear `apps/core/migrations/__init__.py` (paquete nuevo).
- [ ] Crear `apps/core/migrations/anonymize.py` con:
  - [ ] `anonymize_hash(value, salt) -> str` — `sha256(value + salt)[:12]`.
  - [ ] `anonymize_optional(value, salt) -> str | None` — devuelve
        `None` si el input es vacío, sino `anonymize_hash`.
  - [ ] Tests unitarios en
        `apps/core/tests/test_anonymize.py` que validen:
    - determinismo (mismo input → mismo output),
    - irreversibilidad sin `SECRET_SALT` (sanity check),
    - manejo de strings vacíos / None / bytes.

## 3. Validadores

- [ ] Crear `apps/core/migrations/validators.py` con:
  - [ ] `validate_schema(filepath, expected_headers)` — chequea que el
        CSV tenga exactamente los headers esperados.
  - [ ] `validate_no_pii(dataframe, pii_columns)` — chequea regex de
        emails / documentos / teléfonos obvios en columnas
        declaradas como anonimizadas.
  - [ ] `validate_fk_resolution(rows, foreign_key, lookup)` —
        asegura que cada FK en `rows` exista en `lookup`.
  - [ ] Tests unitarios en
        `apps/core/tests/test_validators.py`.

## 4. Comando de migración

- [ ] Crear `apps/core/management/__init__.py` y
      `apps/core/management/commands/__init__.py`.
- [ ] Crear
      `apps/core/management/commands/migrate_legacy_data.py` con:
  - [ ] `--source=<dir>` (requerido, default = `./data/legacy/`).
  - [ ] `--dry-run` (no escribe a la DB, solo reporta).
  - [ ] `--skip-validation` (no recomendado, solo para emergencias).
  - [ ] `--anonymize-salt=<env>` (default = `LEGACY_DATA_SALT`,
        falla si no está seteada en prod).
  - [ ] Lógica: leer cada CSV, validar, anonimizar PII, escribir a
        los modelos correctos, reportar conteos.
  - [ ] Idempotencia: usar `get_or_create` con la clave natural de
        cada modelo (radicado para Solicitud, numero para Acto, etc.).

## 5. Tests del comando

- [ ] Crear `apps/core/tests/test_migrate_legacy_data.py` con:
  - [ ] `test_dry_run_creates_no_records` — usar `call_command` con
        `--dry-run` y verificar que la DB no cambia.
  - [ ] `test_apply_creates_records` — CSV sintético en `tmp_path`,
        ejecutar sin `--dry-run`, verificar conteos.
  - [ ] `test_idempotent` — ejecutar dos veces, verificar mismo
        conteo final.
  - [ ] `test_validation_aborts_on_bad_csv` — CSV con header
        faltante → exit code 1, sin escribir.
  - [ ] `test_anonymize_replaces_pii_fields` — CSV con emails
        reales, verificar que en la DB se persiste el hash.
  - [ ] `test_fk_resolution_failure` — Solicitud sin convocatoria
        correspondiente → aborta con mensaje claro.

## 6. Conformance

- [ ] Agregar al `pyproject.toml` (si falta): `factory-boy>=3.3` y
      `pandas>=2.0` (o `csv` stdlib si se quiere mantener
      minimalista).
- [ ] Agregar a `.gitignore`: `data/`, `*.legacy.csv`,
      `*.legacy.jsonl`. Documentar en
      `docs/migrations/migration-runbook.md` que estos paths son
      intencionales.
- [ ] Verificar con grep que `apps/core/tests/` no contiene PII:
      `grep -rE "@example\.com|1234567890|CC \\d|TI \\d" apps/core/tests/` debe
      devolver 0 hits en archivos de tests (los factories usan
      prefijo `anon-test-`).

## 7. Verificación final

- [ ] `python -c "import ast; ast.parse(open('apps/core/management/commands/migrate_legacy_data.py').read())"`.
- [ ] `python manage.py migrate_legacy_data --dry-run --source=apps/core/tests/fixtures/legacy_sample/`
      corre limpio y reporta conteos.
- [ ] `python manage.py check` no reporta errores.

## 8. Hand-off

- [ ] Escribir `openspec/changes/CHG-099-migration/apply-progress.md`
      con resumen, archivos tocados, comandos de verificación y
      resultados.
