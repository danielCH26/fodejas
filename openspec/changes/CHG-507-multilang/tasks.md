# Tasks — CHG-507 Multilenguaje: Infraestructura i18n y App Piloto Accounts

## 1. Infraestructura i18n en settings

- [ ] 1.1 `config/settings.py`: agregar `LANGUAGES = [("es-CO", "Español"),
      ("en", "English")]` en la sección Internationalization.
- [ ] 1.2 `config/settings.py`: agregar
      `LOCALE_PATHS = [BASE_DIR / "locale"]` en la misma sección.
- [ ] 1.3 `config/settings.py`: insertar
      `"django.middleware.locale.LocaleMiddleware"` en `MIDDLEWARE`
      entre `SessionMiddleware` (índice 4) y `CommonMiddleware`
      (índice 5). Agregar comentario de posición exacto.
- [ ] 1.4 Test: verificar en `test_settings.py` o fixture que
      `LocaleMiddleware` está en `MIDDLEWARE` y en la posición
      correcta (índice 5); que `LANGUAGES` contiene `es-CO` y `en`;
      que `LOCALE_PATHS` resuelve a `BASE_DIR / "locale"`.
- [ ] 1.5 Wiring URL de `set_language` en `config/urls.py`:
      `path("i18n/", include("django.conf.urls.i18n"))` — requerido
      por el switcher (`{% url 'set_language' %}`) y los tests de cambio.

## 2. Estructura locale y script de compilación

- [ ] 2.1 Crear directorio `locale/es_CO/LC_MESSAGES/` con
      `django.po` esqueleto (header con `Language: es-CO`,
      `Content-Type: text/plain; charset=UTF-8`; sin entradas de
      traducción activas — msgids ya son español).
- [ ] 2.2 Crear directorio `locale/en/LC_MESSAGES/` con
      `django.po` esqueleto (header `Language: en`,
      `Content-Type: text/plain; charset=UTF-8`; sin entradas
      activas aún).
- [ ] 2.3 `pyproject.toml`: agregar `polib` a
      `[project.optional-dependencies] dev` (junto a black, pytest, etc.).
- [ ] 2.4 Crear `scripts/compile_mo.py`: script pure-Python que usa
      `polib` para recorrer `locale/*/LC_MESSAGES/django.po`,
      compilar a `.mo` in-place, y reportar errores de sintaxis en
      `.po`. Debe poder ejecutarse como `python scripts/compile_mo.py`.
- [ ] 2.5 Ejecutar `scripts/compile_mo.py` y commitear los `.mo`
      generados en `locale/es_CO/LC_MESSAGES/django.mo` y
      `locale/en/LC_MESSAGES/django.mo`.

## 3. Base y switcher de idioma

- [ ] 3.1 `templates/base.html`: agregar `{% load i18n %}` al inicio.
- [ ] 3.2 `templates/base.html`: cambiar `<html>` por
      `<html lang="{% get_current_language %}">`.
- [ ] 3.3 `templates/base.html`: agregar formulario switcher en la
      navbar (o donde haga sentido para UX): `<form
      action="{% url 'set_language' %}" method="post">` con
      `{% csrf_token %}`, `<input type="hidden" name="language"
      value="{{ LANGUAGE_CODE }}">`, y links/buttons "Español" /
      "English". Usar el mismo patrón que la documentación de Django.
- [ ] 3.4 `templates/base.html`: marcar con `{% trans "..." %}`
      los textos hardcoded del navbar y footer (nombres de nav links,
      Copyright, año, etc.).
- [ ] 3.5 Verificar que el switcher redirige a la página anterior
      tras cambiar idioma (comportamiento estándar de `set_language`).

## 4. App Accounts piloto — marcado de templates

- [ ] 4.1 `apps/accounts/templates/accounts/login.html`: marcar con
      `{% trans "..." %}` todos los textos de labels, placeholders,
      botones, títulos, mensajes de error/success hardcoded.
- [ ] 4.2 `apps/accounts/templates/accounts/register.html`: mismo
      tratamiento.
- [ ] 4.3 `apps/accounts/templates/accounts/profile.html`: mismo
      tratamiento.
- [ ] 4.4 `apps/accounts/templates/accounts/dashboard.html`: mismo
      tratamiento.
- [ ] 4.5 `apps/accounts/templates/accounts/password_reset.html`: mismo.
- [ ] 4.6 `apps/accounts/templates/accounts/password_reset_done.html`:
      mismo.
- [ ] 4.7 `apps/accounts/templates/accounts/password_reset_confirm.html`:
      mismo.
- [ ] 4.8 `apps/accounts/templates/accounts/password_reset_complete.html`:
      mismo.
- [ ] 4.9 `apps/accounts/templates/accounts/partials/login_success.html`:
      mismo si contiene textos.

## 5. App Accounts piloto — traducciones al inglés

- [ ] 5.1 `locale/en/LC_MESSAGES/django.po`: agregar entradas para
      todos los msgids marcados en los templates de accounts (task 4).
      Cada entrada: `msgid "texto español"` → `msgstr "texto inglés"`.
      Usar el msgid exacto del template.
- [ ] 5.2 Verificar que `locale/es_CO/LC_MESSAGES/django.po` tiene
      las mismas entradas con `msgstr ""` (o copia del msgid,
      opcional) — el msgid es el fallback de todas formas.
- [ ] 5.3 Re-ejecutar `scripts/compile_mo.py` para regenerar los `.mo`.

## 6. Páginas públicas — Convocatorias

- [ ] 6.1 `templates/convocatories/index.html`: marcar con `{% trans %}`
      todos los textos de título de página, labels, botones, mensajes.
- [ ] 6.2 `templates/convocatories/detail.html`: mismo.
- [ ] 6.3 `templates/convocatories/form.html`: mismo.

## 7. Páginas públicas — Applications

- [ ] 7.1 `templates/applications/wizard.html`: marcar con `{% trans %}`.
- [ ] 7.2 `templates/applications/partials/wizard_step_1.html` a
      `partials/wizard_step_5.html`: marcar con `{% trans %}` cada
      uno; usar `{% blocktrans %}` donde haya interpolación de variables.
- [ ] 7.3 `templates/applications/list.html`: marcar.
- [ ] 7.4 `templates/applications/detail.html`: marcar.
- [ ] 7.5 `templates/applications/review/list.html`: marcar.
- [ ] 7.6 `templates/applications/review/detail.html`: marcar.
- [ ] 7.7 `templates/applications/review/history.html`: marcar.

## 8. Páginas públicas — Audit

- [ ] 8.1 `templates/audit/base.html`: marcar con `{% load i18n %}` y
      `{% trans %}` los textos del navbar, footer, breadcrumbs.
- [ ] 8.2 `templates/audit/index.html`: marcar.
- [ ] 8.3 `templates/audit/detail.html`: marcar.
- [ ] 8.4 `templates/audit/verify.html`: marcar.

## 9. Páginas públicas — Claims (públicas únicamente)

- [ ] 9.1 Verificar en `apps/claims/views.py` que las vistas
      `ReclamacionCreateView`, `ReclamacionListView`,
      `ReclamacionDetailView`, `ReclamacionUpdateView`,
      `ApelacionCreateView`, `ApelacionListView`,
      `ApelacionDetailView` son públicas (solo `LoginRequiredMixin`).
- [ ] 9.2 `templates/claims/create.html`: marcar con `{% trans %}`.
- [ ] 9.3 `templates/claims/list.html`: marcar.
- [ ] 9.4 `templates/claims/detail.html`: marcar.
- [ ] 9.5 `templates/claims/edit.html`: marcar.
- [ ] 9.6 `templates/claims/apelacion_create.html`: marcar.
- [ ] 9.7 `templates/claims/apelacion_list.html`: marcar.
- [ ] 9.8 `templates/claims/apelacion_detail.html`: marcar.

## 10. Traducciones de páginas públicas al inglés

- [ ] 10.1 `locale/en/LC_MESSAGES/django.po`: agregar entradas para
       todos los msgids de convocatories, applications, audit, claims
       públicos (tasks 6-9). Mantener consistencia de terminología
       con accounts.
- [ ] 10.2 `locale/es_CO/LC_MESSAGES/django.po`: agregar las mismas
       entradas con msgid = msgstr (o vacío; el msgid es el fallback).
- [ ] 10.3 Re-ejecutar `scripts/compile_mo.py`.

## 11. Pruebas de i18n

- [ ] 11.1 Test `test_locale_middleware_position`: verificar que
       `"django.middleware.locale.LocaleMiddleware"` está en
       `settings.MIDDLEWARE` y su índice es mayor que el de
       `SessionMiddleware` y menor que el de `CommonMiddleware`.
- [ ] 11.2 Test `test_languages_setting`: verificar que
       `settings.LANGUAGES` contiene `"es-CO"` y `"en"`.
- [ ] 11.3 Test `test_locale_paths`: verificar que `settings.LOCALE_PATHS`
       contiene al menos una ruta que termina en `"locale"`.
- [ ] 11.4 Test `test_language_switcher_redirect`: client POST a
       `set_language` con `language=en` → assert status 302 +
       assert cookie `django_language` existe.
- [ ] 11.5 Test `test_login_english`: GET `/accounts/login/` con
       `django_language=en` en cookie → `assertContains(response,
       "Login")` (o equivalente en el template).
- [ ] 11.6 Test `test_login_spanish_fallback`: GET `/accounts/login/`
       sin cookie → `assertContains(response, "Iniciar sesión")`.
- [ ] 11.7 Test `test_compile_mo_script`: ejecutar
       `scripts/compile_mo.py` en subprocess → assert exit 0;
       verificar que los `.mo` se generaron en `locale/*/LC_MESSAGES/`.
- [ ] 11.8 Test de cobertura .po: cargar `locale/en/LC_MESSAGES/django.po`
       con polib; verificar que un msgid conocido de accounts tiene
       `msgstr` no vacío.

## 12. Verificación final

- [ ] 12.1 Suite completa: `pytest` con sqlite in-memory → todos verde.
- [ ] 12.2 `python manage.py check` → limpio, sin warnings de i18n.
- [ ] 12.3 Verificar que los PDFs legales
       (`templates/governance/acto_pdf.html`,
       `templates/legalization/pdf/*`) **no** contienen `{% trans %}`.
- [ ] 12.4 Verificar que los templates admin de accounts
       (`apps/accounts/templates/accounts/admin/`) no fueron modificados.
- [ ] 12.5 Verificar que los templates admin de claims
       (`templates/claims/admin/`) no fueron modificados.
