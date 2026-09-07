# CHG-806 — Limpieza de apps stub y placeholder de junta sessions

> Continuación de la remediación de hallazgos AUD-024 (stubs
> registrados sin contenido) y AUD-025 (módulo `governance.sessions`
> inexistente). Cierra los pendientes out-of-scope del plan de fixes
> CHG-801..805.

## Contexto

La auditoría extendida del 2026-09-05 (`docs/audits/extended-audit.md`
§6 + AUD-024 y AUD-025) encontró tres problemas residuales que no
encajaban en ninguno de los 5 changes anteriores:

- **`apps/reporting/`** — stub. 5 de 6 módulos son archivos de 0 bytes.
  Registrado en `INSTALLED_APPS` pero no provee ninguna funcionalidad.
  CAP-020, CAP-021, CAP-027 y CAP-028 están planificados en Fase 5
  (`roadmap.md §9.1`) sin change folder activo en
  `openspec/changes/`.
- **`apps/psychosocial/`** — stub. Mismo patrón. CAP-012 está en Fase 4
  (`roadmap.md §8.1`) sin change folder activo.
- **`apps/governance/sessions/`** — directorio ausente. CAP-017 (sesiones
  de Junta, quórum, votaciones) está en Fase 5 sin change folder activo.

Mantener stubs registrados genera tres riesgos concretos:

1. Cualquier modelo futuro que use una FK hacia un modelo de
   `reporting` o `psychosocial` va a fallar silenciosamente en
   `makemigrations --check` porque la app existe pero no tiene
   `models.py`.
2. `apps/governance/sessions/` no tiene ni `__init__.py`, así que un
   `from apps.governance.sessions import X` futuro rompe con
   `ModuleNotFoundError` en lugar de un error explícito.
3. El AGENTS.md §6 regla 9 ("no romper trazabilidad") se debilita
   cuando hay 0 líneas commiteadas que sugieran "hay algo aquí" sin
   haberlo.

## Capacidades afectadas

- **CAP-012** (Acompañamiento psicosocial, Fase 4 — diferida).
- **CAP-017** (Sesiones de Junta y CT, Fase 5 — diferida).
- **CAP-018** (Conflictos de interés, Fase 5 — diferida).
- **CAP-020** (Informes trimestrales y anuales, Fase 5 — diferida).
- **CAP-021** (Portal de transparencia, Fase 5 — diferida).
- **CAP-027** (Estudio de impacto, Fase 5 — diferida).
- **CAP-028** (Exportación a entes de control, Fase 5 — diferida).

## Reglas de negocio afectadas

- `AGENTS.md` §6 regla 9 (trazabilidad).
- `roadmap.md` §5–§9 (Fase 4 y Fase 5 — fuera de la piloto).

## Cambios propuestos

### Delta en `specs/governance/spec.md`

#### ADDED — § Marcador de sesiones de Junta (CAP-017, Fase 5)

`apps/governance/sessions/` **SHALL** existir como paquete Python
vacío con `__init__.py` y un `README.md` que documente su condición de
placeholder para CAP-017, **aún cuando** su implementación completa
quede diferida a Fase 5 (`roadmap.md §9.1`).

### Cambios concretos

1. **Eliminar `apps/reporting/`**:
   - Borrar el directorio entero (`__init__.py`, `admin.py`,
     `apps.py`, `models.py`, `urls.py`, `views.py`).
   - Quitar `"apps.reporting"` de `INSTALLED_APPS` en
     `config/settings.py`.
2. **Eliminar `apps/psychosocial/`**: mismo tratamiento que
   `apps/reporting/`.
3. **Placeholder para `apps/governance/sessions/`**:
   - Crear `apps/governance/sessions/__init__.py` vacío (sólo el
     docstring del módulo).
   - Crear `apps/governance/sessions/README.md` documentando:
     - CAP-017 (Sesiones de Junta, Fase 5).
     - Roadmap §9.1 — pendiente de `CHG-501-sessions`.
     - Estructura mínima esperada cuando se implemente:
       `models.py` (Sesion, OrdenDelDia, Voto, Quorum, ActaSesion),
       `services/quorum.py`, `services/voting.py`,
       `views/sesiones.py`.
4. **Documentación de retorno**:
   - Crear `docs/stubs-removed.md` con la lista de apps removidas, las
     capacidades que cubren, y los cambios OpenSpec que las
     reintroducirán. Esto evita que un dev futuro "ayude" volviendo
     a crear los stubs.
5. **Verificación de no-regresión**:
   - `python manage.py check` no debe reportar errores por las apps
     removidas.
   - `python manage.py makemigrations --check --dry-run` debe pasar
     sin generar migraciones nuevas.

## Criterios de aceptación

- [ ] `apps/reporting/` y `apps/psychosocial/` no existen en el árbol.
- [ ] `config/settings.py:INSTALLED_APPS` no contiene
      `"apps.reporting"` ni `"apps.psychosocial"`.
- [ ] `apps/governance/sessions/__init__.py` y `README.md` existen.
- [ ] `docs/stubs-removed.md` está commiteado y enlazado desde este
      `proposal.md`.
- [ ] `python manage.py check` corre sin errores.
- [ ] `python -m pytest apps/ -x --no-header -q` no se rompe por las
      apps removidas (los tests previos de CHG-801..805 siguen
      pasando).

## Pruebas

- Smoke test: `apps/stubs_removed/tests.py` (o en `config/tests/`):
  - `test_reporting_removed`: assert not `os.path.exists("apps/reporting")`.
  - `test_psychosocial_removed`: idem.
  - `test_governance_sessions_exists`: assert
    `os.path.exists("apps/governance/sessions/__init__.py")`.
  - `test_settings_installed_apps_no_stubs`: assert
    `"apps.reporting"` and `"apps.psychosocial"` not in
    `settings.INSTALLED_APPS`.
  - `test_stubs_removed_doc_exists`: assert
    `os.path.exists("docs/stubs-removed.md")`.

## Riesgos y Fuera del alcance

- **Riesgo**: si algún test o fixture importa `apps.reporting` o
  `apps.psychosocial`, va a romper. Mitigación: grep
  antes de borrar (ya hecho en este change, 0 matches).
- **Riesgo**: si una dependencia externa (DRF, crispy_forms) se
  engancha al `apps.<nombre>.apps.<X>Config`, puede fallar al
  importar. Mitigación: la búsqueda confirma 0 referencias a esas
  apps en `config/`, así que el riesgo es bajo.
- **Fuera del alcance**:
  - No se implementa `apps/governance/sessions/models.py` ni sus
    servicios. Eso es CHG-501 (Fase 5).
  - No se reintroducen los stubs de reporting/psychosocial. Eso
    ocurrirá cuando se abran los changes de Fase 4/5
    correspondientes.
  - No se modifican apps que sí tienen contenido real, aunque
    pertenezcan a Fase 5 (p.ej. `apps/governance/` que ya existe).

## Referencias

- `docs/audits/extended-audit.md` §6 (stubs), §8.3 AUD-024,
  §8.3 AUD-025.
- `roadmap.md` §8.1 CAP-012, §9.1 CAP-017/018/020/021/027/028.
- `AGENTS.md` §6 regla 9.
