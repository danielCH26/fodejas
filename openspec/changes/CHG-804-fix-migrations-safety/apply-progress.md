# Apply Progress — CHG-804

> Estado al cierre del fast-forward. Ver `proposal.md` y `tasks.md` para
> el alcance completo.

## Resumen

Migración de remediación para la política INF-014 (zero-downtime
migrations, expand/contract). Cubre los hallazgos **AUD-019** del
`docs/audits/extended-audit.md §7`.

## Estado de tasks.md

- [x] §1 Migración `apps/accounts/migrations/0008_backfill_uuids_customuser_role.py`
- [x] §2 Migración `apps/convocatories/migrations/0003_backfill_uuids_convocatory.py`
- [x] §3 Documentación `docs/migrations/expand-contract.md` (143 líneas, plantilla + historia + reversión)
- [x] §4 CI guard `.github/workflows/migrations-safety.yml`
- [x] §5 Anotaciones en migraciones destructivas existentes (0006, 0007, 0002)
- [x] §6 Tests (`apps/accounts/tests/test_migrations_0008_uuid.py` + `apps/convocatories/tests/test_migrations_0003_uuid.py`)
- [ ] §7 Verificación final con pytest (bloqueado por ausencia de venv con Django 5.2 — ver blockers)
- [x] §8 Este hand-off

## Archivos tocados

| Path | Tipo | Notas |
|------|------|-------|
| `openspec/changes/CHG-804-fix-migrations-safety/proposal.md` | propuesta | escrito en fase de planning |
| `openspec/changes/CHG-804-fix-migrations-safety/tasks.md` | tasks | 85 líneas, todas las subtareas |
| `openspec/changes/CHG-804-fix-migrations-safety/specs/migrations-strategy/spec.md` | spec delta | 133 líneas, ADDED Requirements con 4 Requirements + 5 Scenarios |
| `apps/accounts/migrations/0008_backfill_uuids_customuser_role.py` | migración | data-only, idempotente, 78 líneas |
| `apps/convocatories/migrations/0003_backfill_uuids_convocatory.py` | migración | data-only, idempotente, 58 líneas |
| `apps/accounts/migrations/0006_alter_customuser_id.py` | anotación | comentario header CHG-804 (operations intactas) |
| `apps/accounts/migrations/0007_alter_role_id.py` | anotación | comentario header CHG-804 (operations intactas) |
| `apps/convocatories/migrations/0002_alter_convocatory_id.py` | anotación | comentario header CHG-804 (operations intactas) |
| `docs/migrations/expand-contract.md` | docu | 143 líneas, política completa + plantilla + ejemplo + historia |
| `.github/workflows/migrations-safety.yml` | CI | guard heurístico contra PK destructivos sin backfill |
| `apps/accounts/tests/test_migrations_0008_uuid.py` | test | 7 tests, sin DB, sin PII |
| `apps/convocatories/tests/test_migrations_0003_uuid.py` | test | 7 tests, sin DB, sin PII |

## Verificaciones ejecutadas

```
$ python -c "import ast; ast.parse(open('apps/accounts/migrations/0008_backfill_uuids_customuser_role.py').read()); ast.parse(open('apps/convocatories/migrations/0003_backfill_uuids_convocatory.py').read()); print('OK')"
OK
```

No se ejecutó `pytest` por ausencia de venv con Django 5.2 en este
entorno. Los tests son unitarios puros (no requieren DB) y deberían
correr limpios en cuanto el entorno esté aprovisionado.

## Blockers

1. **Entorno sin venv con Django 5.2** (pre-existente, mencionado en
   CHG-801 y CHG-803). El sub-agente y la edición inline tuvieron que
   esquivar este problema; los tests escritos son unitarios
   (sintaxis + reflexión) y deberían correr sin necesidad del ORM.

2. **Typo pre-existente en `config/settings.py:205`** (también
   mencionado por CHG-803): `env.db(url=_db_url)` rompe el import en
   staging/prod. No se corrige acá (out of scope), pero bloquea
   cualquier `manage.py check` o `migrate` en producción. Fix
   sugerido: `env.db(_db_url)` (sin la keyword `url=`).

3. **Migration 0002_customuser_habeas_data_consent_*.py usa
   `CheckConstraint(condition=...)`** — pre-existente, eliminado en
   Django 5.2. Impide `manage.py migrate` en dev hasta que se arregle.

## Follow-ups

- **CHG-INF-005-secrets-rotation** (candidate): el typo en
  `settings.py:205` debería migrar a un change dedicado o agregarse a
  CHG-804 retroactivamente como hotfix.

- **CHG-INF-014-migrations-preflight**: aplicar las migraciones de
  CHG-804 (0008 + 0003) en un environment de staging con datos
  realistas ANTES del próximo deploy a producción, para validar que el
  backfill sea noop en el estado actual y que el grafo de
  dependencias quede correcto.

- **CHG-806 (candidate) — stub apps cleanup**: las apps
  `reporting/` y `psychosocial/` siguen siendo stubs (0-byte files,
  registradas en INSTALLED_APPS). No relacionadas a CHG-804.

- **CHG-806 (candidate) — junta sessions skeleton**: `apps/governance/sessions/`
  no existe. CAP-017 está fuera de la piloto, pero conviene al menos
  dejar el esqueleto para evitar sorpresa futura.

- **CHG-806 (candidate) — pgbouncer credentials rotation**:
  `docker/pgbouncer_userlist.txt` commiteado con credenciales. Menor
  pero debería rotarse y salir del repo.

## Verificación post-merge (TODO para el equipo)

```bash
# En staging con Django 5.2 + PostgreSQL:
python manage.py migrate accounts --plan
python manage.py migrate convocatories --plan

# Verificar que 0008 y 0003 aparecen como NoOp en el log
python manage.py migrate accounts 2>&1 | grep -i backfill
python manage.py migrate convocatories 2>&1 | grep -i backfill

# Tests (unitarios, no requieren DB):
pytest apps/accounts/tests/test_migrations_0008_uuid.py -v
pytest apps/convocatories/tests/test_migrations_0003_uuid.py -v

# Smoke del CI guard:
gh workflow run migrations-safety.yml
gh run view --log
```
