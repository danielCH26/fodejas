# spec.md — CHG-507 Multilenguaje: Infraestructura i18n y App Piloto Accounts

## ADDED

### ADDED — Selección de idioma persistente (cookie)

El sistema SHALL soportar la selección de idioma entre `es-CO`
(español de Colombia, default) e `en` (inglés). La selección SHALL
persistirse en el cookie `django_language`. El sistema SHALL aplicar
el idioma persistido en todas las requests subsecuentes del mismo
usuario sin necesidad de volver a seleccionar.

El idioma persistido SHALL tener prioridad sobre la configuración
`LANGUAGE_CODE` de Django (`es-CO`). Si el cookie no existe,
el sistema SHALL usar `es-CO` como idioma activo.

**Referencia**: `project.md §5.1` (UI en español, ahora disponible
también en inglés); `config/settings.py:277` (`LANGUAGE_CODE`).

---

### ADDED — LocaleMiddleware y configuración LANGUAGES/LOCALE_PATHS

El sistema SHALL incluir `django.middleware.locale.LocaleMiddleware`
en `config/settings.py` en la posición correcta dentro de
`MIDDLEWARE`: **después** de `SessionMiddleware` y **antes** de
`CommonMiddleware`. Esta posición es necesaria para que el middleware
pueda leer el idioma de la cookie/sesión y establecerlo antes de que
`CommonMiddleware` procese la URL con prefix default.

El sistema SHALL declarar `LANGUAGES = [("es-CO", "Español"), ("en",
"English")]` en `config/settings.py`. El sistema SHALL declarar
`LOCALE_PATHS = [BASE_DIR / "locale"]` en `config/settings.py`.

**Referencia**: `config/settings.py:166-177` (MIDDLEWARE actual);
`config/settings.py:277-282` (sección Internationalization existente).

---

### ADDED — Archivos de traducciones .po/.mo y compilación reproducible

El sistema SHALL proporcionar archivos `django.po` en la ruta
`locale/{es_CO,en}/LC_MESSAGES/` con el formato estándar de gettext.
Para `es-CO`, el archivo `django.po` SHALL contener los msgids
(texto en español actual) con `msgstr` vacío o igual al msgid;
el archivo `.mo` correspondiente es optativo para es-CO ya que
el fallback a msgid es correcto.

Para `en`, el archivo `django.po` SHALL contener los msgids en
español y sus `msgstr` correspondientes en inglés para todos los
strings del slice. El sistema SHALL generar `locale/en/LC_MESSAGES/django.mo`
desde `locale/en/LC_MESSAGES/django.po` mediante el script
`scripts/compile_mo.py` (pure-Python, usa la librería `polib`).

Los archivos `.mo` compilados SHALL ser commiteados al repositorio
junto con sus `.po` fuentes. El sistema SHALL poder regenerar los
`.mo` idempotentemente desde los `.po` ejecutando
`python scripts/compile_mo.py`.

**Referencia**: `roadmap.md:437` (CHG-507-multilang);
`pyproject.toml` (dependencies dev).

---

### ADDED — Marcado de templates del slice con {% trans %} y {% blocktrans %}

Los siguientes templates SHALL utilizar `{% load i18n %}` al inicio
y marcar todos sus textos visibles con `{% trans "texto" %}` o,
para textos con interpolación de variables,
`{% blocktrans %}texto con {{ variable }}{% endblocktrans %}`:

**Accounts** (app piloto, `apps/accounts/templates/accounts/`):
`login.html`, `register.html`, `profile.html`, `dashboard.html`,
`password_reset.html`, `password_reset_done.html`,
`password_reset_confirm.html`, `password_reset_complete.html`,
`partials/login_success.html`.

**Convocatorias** (`templates/convocatories/`): `index.html`,
`detail.html`, `form.html`.

**Applications** (`templates/applications/`): `wizard.html`,
`partials/wizard_step_1.html` a `partials/wizard_step_5.html`,
`list.html`, `detail.html`, `review/list.html`,
`review/detail.html`, `review/history.html`.

**Audit** (`templates/audit/`): `base.html`, `index.html`,
`detail.html`, `verify.html`.

**Claims — públicos** (`templates/claims/`):
`create.html`, `list.html`, `detail.html`, `edit.html`,
`apelacion_create.html`, `apelacion_list.html`, `apelacion_detail.html`.
Los templates admin (`claims/admin/list.html`,
`apelacion_admin_list.html`) NO SHALL ser modificados en este slice.

**Base** (`templates/base.html`): SHALL agregar
`lang="{% get_current_language %}"` en `<html>`, `{% load i18n %}`,
y marcar los textos de navbar y footer con `{% trans %}`.

---

### ADDED — Switcher de idioma accesible en la navegación

El sistema SHALL proporcionar un mecanismo de switcher de idioma
visible en la navegación principal (navbar del `base.html`).
El switcher SHALL presentar opciones "Español" e "Inglés" (o
"English" cuando ya esté activo el inglés). Al seleccionar una
opción, el sistema SHALL enviar un POST a `django.views.i18n.set_language`
con el código del idioma seleccionado. La respuesta SHALL ser una
redirección HTTP 302 a la URL anterior con el cookie
`django_language` establecido al idioma elegido. El switcher SHALL
mantener la accesibilidad (links o botones con label claro).

---

### ADDED — Exclusión de documentos legales PDF de la traducción

Los siguientes paths SHALL **no** contener marcas `{% trans %}` ni
ser incluidos en los `.po` del sistema:

- `templates/governance/acto_pdf.html`
- `templates/legalization/pdf/*` (todos los documentos)
- Cualquier template de instrumentos legales formales
  (pagaré, contrato, carta de instrucciones)

Estos documentos son instrumentos formales del Archipiélago de San
Andrés y Providencia y SHALL permanecer exclusivamente en español
en todas las iteraciones del proyecto.

---

### ADDED — Pruebas de infraestructura i18n y regresión

El sistema SHALL incluir pruebas automatizadas (en la suite pytest)
que verifiquen:

1. `LocaleMiddleware` está presente en `MIDDLEWARE` de settings y en
   la posición correcta (entre `SessionMiddleware` y `CommonMiddleware`).
2. `LANGUAGES` en settings contiene `"es-CO"` y `"en"`.
3. `LOCALE_PATHS` resuelve a `BASE_DIR / "locale"`.
4. El switcher de idioma (POST a `set_language`) establece el cookie
   `django_language` y redirige con código 302.
5. Con cookie `django_language=en`, GET a `/accounts/login/` contiene
   textos en inglés (`assertContains`).
6. Con cookie `django_language=es-CO` (o sin cookie), GET a
   `/accounts/login/` contiene textos en español actual
   (`assertContains("Iniciar sesión")`, `assertContains("Registrarse")`).
7. Los tests existentes de `apps.accounts` que assertan texto
   español (`"Ya existe una cuenta"`, `"Convocatorias"`,
   `"Postulaciones"`, `"al menos 8 caracteres"`) pasan sin modificación.
8. El script `scripts/compile_mo.py` termina con exit code 0
   y genera los archivos `.mo` correspondientes.

---

## MODIFIED

*(Ninguno en este slice — settings.py solo agrega; no modifica lógica
existente.)*

## RENAMED

*(Ninguno en este slice.)*

## Escenarios

### Scenario: Cambio de idioma a inglés persiste en cookie

**GIVEN** un usuario sin cookie `django_language` establecido
**WHEN** el usuario hace POST a `/i18n/set_language/` con
  `language=en` y `csrfmiddlewaretoken=<token>`
**THEN** la respuesta es HTTP 302 (redirect)
**AND** el header `Set-Cookie` incluye `django_language=en`
**AND** en el request siguiente a cualquier página, el idioma
  activo es `en`

### Scenario: Login muestra textos en inglés con cookie en

**GIVEN** un usuario con cookie `django_language=en`
**WHEN** GET `/accounts/login/`
**THEN** el HTML contiene las cadenas en inglés del slice
  (ej. "Login", "Register", o sus equivalentes en el template)
**AND** NO contiene "Iniciar sesión" como texto principal de título
  de página

### Scenario: es-CO muestra texto español actual (regresión cero)

**GIVEN** un usuario sin cookie o con cookie `django_language=es-CO`
**WHEN** GET `/accounts/login/`
**THEN** el HTML contiene "Iniciar sesión" y "Registrarse"
**AND** el HTML renderizado es **byte-idéntico** al renderizado
  anterior a este cambio para las páginas del slice
**AND** los tests existentes de `apps.accounts.tests` pasan
  sin modificación

### Scenario: PDF legal permanece en español

**GIVEN** cualquier idioma activo (`es-CO` o `en`)
**WHEN** se renderiza `templates/governance/acto_pdf.html`
  o cualquier template bajo `templates/legalization/pdf/`
**THEN** el documento contiene solo texto en español
**AND** ninguna cadena de esos templates aparece en los `.po`
  del slice

### Scenario: compile_mo.py genera .mo idempotentes

**GIVEN** los archivos `.po` en `locale/*/LC_MESSAGES/`
**WHEN** se ejecuta `python scripts/compile_mo.py`
**THEN** la ejecución termina con exit code 0
**AND** se generan archivos `django.mo` junto a sus `django.po`
**AND** re-ejecutar el script produce los mismos `.mo`
  (idempotencia)
