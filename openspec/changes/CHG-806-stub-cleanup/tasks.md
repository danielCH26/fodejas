# Tasks — CHG-806 Limpieza de apps stub y placeholder de junta sessions

> Referencia: `proposal.md`. Plantilla según `AGENTS.md` §4.

## 1. Eliminar `apps/reporting/`

- [ ] Borrar `apps/reporting/__init__.py`.
- [ ] Borrar `apps/reporting/admin.py`.
- [ ] Borrar `apps/reporting/apps.py`.
- [ ] Borrar `apps/reporting/models.py`.
- [ ] Borrar `apps/reporting/urls.py`.
- [ ] Borrar `apps/reporting/views.py`.
- [ ] Borrar el directorio `apps/reporting/` (queda vacío).
- [ ] Quitar `"apps.reporting"` de `INSTALLED_APPS` en
      `config/settings.py` (línea ~145).

## 2. Eliminar `apps/psychosocial/`

- [ ] Borrar `apps/psychosocial/__init__.py`.
- [ ] Borrar `apps/psychosocial/admin.py`.
- [ ] Borrar `apps/psychosocial/apps.py`.
- [ ] Borrar `apps/psychosocial/models.py`.
- [ ] Borrar `apps/psychosocial/urls.py`.
- [ ] Borrar `apps/psychosocial/views.py`.
- [ ] Borrar el directorio `apps/psychosocial/`.
- [ ] Quitar `"apps.psychosocial"` de `INSTALLED_APPS` en
      `config/settings.py` (línea ~142).

## 3. Crear placeholder `apps/governance/sessions/`

- [ ] Crear `apps/governance/sessions/__init__.py` con docstring que
      mencione CAP-017.
- [ ] Crear `apps/governance/sessions/README.md` documentando:
  - [ ] CAP-017 (Sesiones de Junta y CT, `roadmap.md §9.1`).
  - [ ] Diferido a Fase 5 (`roadmap.md §9.1`).
  - [ ] Change OpenSpec que lo implementará: `CHG-501-sessions`.
  - [ ] Estructura mínima esperada (models.py, services/, views/).

## 4. Documentación de retorno

- [ ] Crear `docs/stubs-removed.md` con:
  - [ ] Tabla de apps removidas + CAP-NNN + change OpenSpec que las
        reintroducirá.
  - [ ] Justificación del cambio (riesgos de mantener stubs).
  - [ ] Cómo reintroducir cuando llegue el momento.

## 5. Tests

- [ ] Crear `apps/tests/test_stubs_removed.py` con tests:
  - [ ] `test_reporting_directory_does_not_exist`.
  - [ ] `test_psychosocial_directory_does_not_exist`.
  - [ ] `test_governance_sessions_package_exists`.
  - [ ] `test_governance_sessions_has_readme`.
  - [ ] `test_settings_installed_apps_excludes_stubs`.
  - [ ] `test_stubs_removed_doc_exists`.

## 6. Verificación final

- [ ] `python -c "import ast; ast.parse(open('config/settings.py').read()); print('OK')"`.
- [ ] `python manage.py check` no reporta errores.
- [ ] `python -m pytest apps/tests/test_stubs_removed.py --no-header -q`.

## 7. Hand-off

- [ ] Escribir `openspec/changes/CHG-806-stub-cleanup/apply-progress.md`.
