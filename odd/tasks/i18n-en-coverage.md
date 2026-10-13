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

- [ ] T1: Tests i18n RED (nav + placeholders + transparencia + errors).
- [ ] T2: Envolver textos (transparencia, audit, claims, roles.html),
      placeholders con gettext_lazy en forms, `_()` en ValidationErrors;
      opciones de claims → `get_tipo_display`.
- [ ] T3: Actualizar catálogo en (makemessages + msgstr manuales) y
      compilar .mo; tests GREEN.
- [ ] T4: Verificación en vivo: switch a EN en el browser (nav + una
      página transparencia), screenshot.
- [ ] T5: Work-unit commit + evidencia.

## Evidencia

- Commit: _pendiente_
- Verificación: _pendiente_
