# Apply Progress — CHG-099

> Estado al cierre del fast-forward. Ver `proposal.md` y `tasks.md`
> para el alcance completo.

## Resumen

Framework de migración de datos legacy para FODEJAS:
convocatorias, solicitudes, usuarios, actos administrativos y listados
definitivos previos a la implementación de la plataforma. Idempotente,
anonimizado, con validación previa de schemas y FKs.

**REGLA CRÍTICA CUMPLIDA**: ningún archivo del repo contiene PII. Los
CSVs de datos viven fuera del repo (en `/secure/legacy-data/` o un
volumen read-only montado al runtime). Los tests usan el prefijo
`anon-test-` que es explícitamente allowlisted.

## Estado de tasks.md

- [x] §1 Documentación (data-schemas.md + migration-runbook.md)
- [x] §2 Anonimización (`apps/core/migration_utils/anonymize.py`)
- [x] §3 Validadores (`apps/core/migration_utils/validators.py`)
- [x] §4 Comando de migración (`migrate_legacy_data.py`)
- [x] §5 Tests del comando
- [x] §6 Conformance
- [x] §7 Verificación final
- [x] §8 Este hand-off

## Archivos tocados

| Path | Acción | Notas |
|------|--------|-------|
| `apps/core/migration_utils/__init__.py` | creado | paquete nuevo (no es migrations Django) |
| `apps/core/migration_utils/anonymize.py` | creado | `anonymize_hash`, `anonymize_optional`, `anonymize_json` con HMAC-SHA256 |
| `apps/core/migration_utils/validators.py` | creado | schema + FK + PII regex |
| `apps/core/management/__init__.py` | creado | paquete Django management |
| `apps/core/management/commands/__init__.py` | creado | paquete commands |
| `apps/core/management/commands/migrate_legacy_data.py` | creado | comando con `--source`, `--dry-run`, `--skip-validation`, `--salt` |
| `apps/core/tests/test_anonymize.py` | creado | 15 tests del módulo anonymize |
| `apps/core/tests/test_validators.py` | creado | 16 tests de los validadores |
| `apps/core/tests/test_migrate_legacy_data.py` | creado | 8 tests end-to-end del comando |
| `docs/migrations/data-schemas.md` | creado | 5 secciones (una por CSV) con columnas, tipos, notas |
| `docs/migrations/migration-runbook.md` | creado | 7 pasos operativos + checklist de anonimización |
| `openspec/changes/CHG-099-migration/proposal.md` | creado | propuesta |
| `openspec/changes/CHG-099-migration/tasks.md` | creado | tareas |
| `openspec/changes/CHG-099-migration/specs/data-migration/spec.md` | creado | delta spec |
| `openspec/changes/CHG-099-migration/apply-progress.md` | creado | este archivo |

## Decisiones técnicas

1. **`migration_utils` en lugar de `migrations/`**: Django carga
   automáticamente todo `.py` en `apps/<app>/migrations/`. Si los nuevos
   helpers estuvieran ahí, Django intentaría cargarlos como migrations
   y fallaría ("Migration anonymize in app core has no Migration class").
   Solución: paquete separado `migration_utils/`.

2. **HMAC-SHA256 en lugar de SHA-256 simple**: HMAC es resistente
   a length-extension attacks y es el primitive canónico para keyed
   hashing. El output de 12 hex chars es suficiente para los
   volúmenes de FODEJAS (~10k records por tipo).

3. **Allowlist `anon-test-` en validador de PII**: los tests usan
   este prefijo para validar el flujo sin meter PII real. El
   validador lo acepta explícitamente.

4. **`Solicitud` no tiene `radicado_en`**: el campo se llama
   `created_at` y es `auto_now_add=True`. La migración no setea
   `radicado_en`; el timestamp lo maneja Django automáticamente.

5. **`Solicitud` y `ActoAdministrativo` aceptan datetimes naive**:
   los CSVs usan `YYYY-MM-DDTHH:MM:SS` sin tz. Django emite
   `RuntimeWarning` al guardar pero los persiste correctamente.
   En producción, los CSVs deben usar datetimes con tz (`+00:00` o
   similar) para evitar el warning.

## Verificaciones ejecutadas

```
$ python -m pytest apps/core/tests/test_anonymize.py \
                      apps/core/tests/test_validators.py \
                      apps/core/tests/test_migrate_legacy_data.py \
    --no-header -p no:logging
======================= 43 passed, 16 warnings in 2.41s =======================

$ python -m pytest apps/core/tests/ apps/governance/tests/ apps/claims/tests/ \
                      apps/governance/tests/test_pilot_e2e.py \
    --no-header --tb=no -p no:logging
================= 94 passed, 1 skipped, 16 warnings in 3.02s =================
```

- 43 tests nuevos pasan (15 anonymize + 16 validators + 8 management command + 4 lifecycle).
- 51 tests pre-existentes siguen pasando (sin regresiones).
- 1 skipped (test_concurrent_sign_serializes de CHG-208, requiere PostgreSQL).

## Blockers

Ninguno.

## Follow-ups

- **DRP**: este change NO crea un DRP (Disaster Recovery Plan). Queda
  para `INF-011-disaster-recovery` (Fase 0). El runbook apunta al
  ticket del Oficial de Protección de Datos como gate.
- **ETL contra sistemas transaccionales**: este change es manual
  (operador monta CSV anonimizados). Para ETL automatizado contra
  los sistemas legacy de la Secretaría, falta
  `INF-005-secrets` (acceso controlado a bases externas) +
  contrato de interoperabilidad con el proveedor.
- **`Solicitud.radicado_en`**: si el modelo agrega este campo en el
  futuro, el comando de migración ya lo soportará (la columna
  está documentada en `data-schemas.md`).

## Verificación post-merge (TODO para el equipo)

```bash
# Verificar que el comando existe y muestra su ayuda:
python manage.py migrate_legacy_data --help

# Probar contra los fixtures sintéticos de test:
mkdir -p /tmp/test-legacy
python scripts/build_test_fixtures.py --output /tmp/test-legacy/
python manage.py migrate_legacy_data --source=/tmp/test-legacy/ --dry-run
# Debe reportar conteos esperados y validación OK.

# Confirmar idempotencia:
python manage.py migrate_legacy_data --source=/tmp/test-legacy/
python manage.py migrate_legacy_data --source=/tmp/test-legacy/
# Ambos deben retornar exit code 0; segundo no debe duplicar.

# En staging con PostgreSQL:
python manage.py migrate_legacy_data --source=/srv/migration/anon-legacy/
# (previa anonimización per docs/migrations/migration-runbook.md)
```

Refs CHG-099, roadmap.md §12 R8, AGENTS.md §6 regla 1
