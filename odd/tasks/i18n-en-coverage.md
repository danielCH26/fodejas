# i18n: cobertura completa al cambiar a inglés

> Pedido del usuario (sesión 2026-10-12): «Revisa que todos los textos y
> placeholders se traduzcan al cambiar a inglés». Auditoría previa con
> gentle-ai-explore sobre templates, forms y catálogo en.

## Estado de partida (auditoría)

- Catálogo `locale/en/LC_MESSAGES/django.po`: 829 msgids, sin msgstr
  vacíos ni fuzzy. Base sana.
- **Faltan 5 msgids** del sidebar nuevo: «Navegación principal», «Menú
  móvil», «Abrir menú», «Cerrar menú», «Transparencia».
- **~18 textos visibles sin envolver** en `templates/transparencia/`
  (marca, links, card titles, `<th>`, párrafos) + audit/index y
  claims/create.html (options hardcodeadas; el modelo ya tiene `_()`).
- **~18 placeholders hardcodeados** en `apps/accounts/forms.py` (login,
  registro, reset) y `roles.html`.
- **8 ValidationErrors sin `_()`** en `apps/accounts/forms.py`,
  `apps/accounts/forms/admin.py`, `apps/claims/services/transitions.py`.

## Decisiones

1. Se corrige TODO el hallazgo en **un solo work-unit commit** (una
   preocupación: cobertura EN), sobre `feat/ui-sidebar-nav`.
2. Test-first aplicable: tests deterministas con `activate('en')` que
   fallan antes del arreglo (RED) y pasan después (GREEN) — strings del
   nav, placeholder renderizado del form de login/registro, textos de
   transparencia.
3. `compilemessages` requiere gettext/msgfmt; si no está instalado,
   compilar `.mo` con `polib` (script one-off, sin agregar dependencia).
4. Msgstr nuevos en en: traducción manual (msgstr vacío = fallback a
   español = defecto).

## Tareas

- [x] T1: Tests i18n RED (nav + placeholders + transparencia + errors).
- [x] T2: Envolver textos (transparencia, audit, claims, roles.html),
      placeholders con gettext_lazy en forms, `_()` en ValidationErrors;
      opciones de claims → `get_tipo_display`.
- [x] T3: Actualizar catálogo en (57 + 50 pares) y compilar .mo (polib);
      tests GREEN (27).
- [x] T4: Verificación en vivo: switch EN vía cookie django_language
      (click de form-submit tiene limitación en el runtime de Orca).
      Ronda 2 tras hallazgos del verify: labels inyectados por
      accounts_views.py con gettext_lazy, subpáginas actos/convocatorias,
      párrafos index, estadisticas. Fix final: blocktrans multi-línea
      extraía msgid con \n → unificado a una línea; render check
      "Welcome, <name>" en vivo PASS. ES restaurado. 0 errores consola.
      Datos de DB (nombre de usuario, role.name) quedan en español por
      diseño — no son alcanzables por catálogo i18n.
- [x] T5: Work-unit commits `82633c3`, `1070c44`, `4b00398` en
      `feat/ui-sidebar-nav` + revisión nativa del rango.

## Evidencia

- Tests: 27 i18n RED→GREEN; accounts 116 passed; manage.py check clean.
- Verificación browser: en-dashboard/en-transparencia/en-actos/
  en-convocatorias PASS; saludo PASS tras fix final; ES restaurado.
- Commits: `82633c3`, `1070c44`, `4b00398`.
- Desviación anotada: `scripts/compile_mo.py` creado por el worker
  (fuera de superficies); se conserva por necesidad (sin msgfmt en
  Windows), documentado y determinista.
