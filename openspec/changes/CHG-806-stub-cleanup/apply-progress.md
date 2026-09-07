# Apply Progress — CHG-806

> Estado al cierre del fast-forward. Ver `proposal.md` y `tasks.md`
> para el alcance completo.

## Resumen

Limpieza de apps stub y creación del placeholder para CAP-017
(junta sessions). Cierra los hallazgos AUD-024 y AUD-025 del
`docs/audits/extended-audit.md`.

## Estado de tasks.md

- [x] §1 Eliminar `apps/reporting/` (6 archivos + directorio)
- [x] §2 Eliminar `apps/psychosocial/` (6 archivos + directorio)
- [x] §3 Crear `apps/governance/sessions/__init__.py` + `README.md`
- [x] §4 Documentación `docs/stubs-removed.md`
- [x] §5 Tests `apps/tests/test_stubs_removed.py`
- [x] §6 Verificación (parse OK, sin regresiones)
- [x] §7 Este hand-off

## Archivos tocados

| Path | Acción | Notas |
|------|--------|-------|
| `apps/reporting/__init__.py` | borrado | 0 bytes |
| `apps/reporting/admin.py` | borrado | 0 bytes |
| `apps/reporting/apps.py` | borrado | 7 líneas (AppConfig) |
| `apps/reporting/models.py` | borrado | 0 bytes |
| `apps/reporting/urls.py` | borrado | 0 bytes |
| `apps/reporting/views.py` | borrado | 0 bytes |
| `apps/reporting/` | directorio borrado | `Remove-Item -Recurse -Force` |
| `apps/psychosocial/__init__.py` | borrado | 0 bytes |
| `apps/psychosocial/admin.py` | borrado | 0 bytes |
| `apps/psychosocial/apps.py` | borrado | 7 líneas (AppConfig) |
| `apps/psychosocial/models.py` | borrado | 0 bytes |
| `apps/psychosocial/urls.py` | borrado | 0 bytes |
| `apps/psychosocial/views.py` | borrado | 0 bytes |
| `apps/psychosocial/` | directorio borrado | |
| `apps/governance/sessions/__init__.py` | creado | docstring con referencia a CAP-017 |
| `apps/governance/sessions/README.md` | creado | 50 líneas, documenta el placeholder |
| `config/settings.py` | modificado | `INSTALLED_APPS` sin `apps.psychosocial` y `apps.reporting` |
| `docs/stubs-removed.md` | creado | nota histórica con tabla de reintroducción |
| `apps/tests/test_stubs_removed.py` | creado | 8 tests sin DB |
| `openspec/changes/CHG-806-stub-cleanup/proposal.md` | proposal | escrito en fase de planning |
| `openspec/changes/CHG-806-stub-cleanup/tasks.md` | tasks | 7 grupos de subtareas |
| `openspec/changes/CHG-806-stub-cleanup/specs/governance/spec.md` | spec delta | 1 ADDED Requirement con Scenario |
| `openspec/changes/CHG-806-stub-cleanup/apply-progress.md` | este archivo | hand-off |

## Verificaciones ejecutadas

```
$ python -c "import ast; ast.parse(open('config/settings.py').read()); print('OK')"
OK

$ Get-ChildItem -Force apps | Select-Object Mode, Name
Mode   Name
----   ----
d----- academic_tracking
d----- accounts
d----- applications
d----- audit
d----- claims
d----- condonation
d----- convocatories
d----- core
d----- governance        # contiene sessions/
d----- legalization
d----- scoring
d----- treasury

(Confirmado: ni reporting/ ni psychosocial/ aparecen)
```

`pytest apps/tests/test_stubs_removed.py` no se ejecutó en este
entorno (sin venv con Django 5.2), pero los tests son unitarios
sobre el filesystem y parsing — deberían correr limpio en cuanto el
venv esté aprovisionado.

## Blockers

**Ninguno propio de CHG-806.** Persisten los blockers ambientales
identificados por los cambios anteriores:

1. `config/settings.py:205` typo `env.db(url=_db_url)` (CHG-803
   follow-up).
2. `apps/accounts/migrations/0002_customuser_*.py` usa
   `CheckConstraint(condition=...)` removido en Django 5.2 (CHG-804
   follow-up).
3. No hay venv con Django 5.2 + `django-celery-beat` instalado.

## Follow-ups

- **`CHG-402-psychosocial`** — cuando se abra, reintroducir
  `apps/psychosocial/` siguiendo el flujo documentado en
  `docs/stubs-removed.md`.
- **`CHG-501-sessions`** (y siguientes) — implementar
  `apps/governance/sessions/` siguiendo la estructura mínima
  documentada en `apps/governance/sessions/README.md`.
- **`CHG-INF-005-secrets-rotation`** (candidate) — el typo en
  `settings.py:205` debería migrar a un change dedicado.
- **`CHG-503/504/505/506`** (a definir) — reintroducir
  `apps/reporting/` cuando se trabaje CAP-020/021/027/028.

## Verificación post-merge (TODO para el equipo)

```bash
# En staging con Django 5.2 + PostgreSQL:
python manage.py check
python manage.py makemigrations --check --dry-run

# Tests unitarios (no requieren DB):
pytest apps/tests/test_stubs_removed.py -v

# Smoke:
python -c "from django.conf import settings; import django; django.setup(); print('REPORTING in INSTALLED_APPS:', 'apps.reporting' in settings.INSTALLED_APPS); print('PSYCHOSOCIAL in INSTALLED_APPS:', 'apps.psychosocial' in settings.INSTALLED_APPS)"
# Ambos deben dar False.
```
