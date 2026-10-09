# Tasks — CHG-806 Limpieza de apps stub y placeholder de junta sessions

> Referencia: `proposal.md`. Plantilla según `AGENTS.md` §4.

## 1. Eliminar `apps/reporting/`

- [x] Borrar `apps/reporting/__init__.py`.
- [x] Borrar `apps/reporting/admin.py`.
- [x] Borrar `apps/reporting/apps.py`.
- [x] Borrar `apps/reporting/models.py`.
- [x] Borrar `apps/reporting/urls.py`.
- [x] Borrar `apps/reporting/views.py`.
- [x] Borrar el directorio `apps/reporting/` (queda vacío).
- [x] Quitar `"apps.reporting"` de `INSTALLED_APPS` en
      `config/settings.py` (línea ~145).

## 2. Eliminar `apps/psychosocial/`

- [x] Borrar `apps/psychosocial/__init__.py`.
- [x] Borrar `apps/psychosocial/admin.py`.
- [x] Borrar `apps/psychosocial/apps.py`.
- [x] Borrar `apps/psychosocial/models.py`.
- [x] Borrar `apps/psychosocial/urls.py`.
- [x] Borrar `apps/psychosocial/views.py`.
- [x] Borrar el directorio `apps/psychosocial/`.
- [x] Quitar `"apps.psychosocial"` de `INSTALLED_APPS` en
      `config/settings.py` (línea ~142).

## 3. Crear placeholder `apps/governance/sessions/`

- [x] Crear `apps/governance/sessions/__init__.py` con docstring que
      mencione CAP-017.
- [x] Crear `apps/governance/sessions/README.md` documentando:
  - [ ] CAP-017 (Sesiones de Junta y CT, `roadmap.md §9.1`).
  - [ ] Diferido a Fase 5 (`roadmap.md §9.1`).
  - [ ] Change OpenSpec que lo implementará: `CHG-501-sessions`.
  - [ ] Estructura mínima esperada (models.py, services/, views/).

## 4. Documentación de retorno

- [x] Crear `docs/stubs-removed.md` con:
  - [ ] Tabla de apps removidas + CAP-NNN + change OpenSpec que las
        reintroducirá.
  - [ ] Justificación del cambio (riesgos de mantener stubs).
  - [ ] Cómo reintroducir cuando llegue el momento.

## 5. Tests

- [x] Crear `apps/tests/test_stubs_removed.py` con tests:
  - [ ] `test_reporting_directory_does_not_exist`.
  - [ ] `test_psychosocial_directory_does_not_exist`.
  - [ ] `test_governance_sessions_package_exists`.
  - [ ] `test_governance_sessions_has_readme`.
  - [ ] `test_settings_installed_apps_excludes_stubs`.
  - [ ] `test_stubs_removed_doc_exists`.

## 6. Verificación final

- [x] `python -c "import ast; ast.parse(open('config/settings.py').read()); print('OK')"`.
- [x] `python manage.py check` no reporta errores.
- [x] `python -m pytest apps/tests/test_stubs_removed.py --no-header -q`.

## 7. Hand-off

- [x] Escribir `openspec/changes/CHG-806-stub-cleanup/apply-progress.md`.
