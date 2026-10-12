# CHG-507 — Multilenguaje: Infraestructura i18n y App Piloto Accounts (CAP-030)

## Contexto

CAP-030 ("Multidioma y Trilingüismo") es P3 en `project.md §8` y en
`roadmap.md:437` se registra como "CHG-507-multilang | i18n
español/inglés/creole | apps/accounts/". La convención del proyecto
(`project.md §5.1`) establece que el código va en inglés y la UI/docs
en español; no existe aún ninguna infraestructura de internacionalización.

El estado actual del proyecto en materia de i18n es **cero**:

- `config/settings.py:277` — `LANGUAGE_CODE = "es-CO"` existe pero
  **no hay** setting `LANGUAGES`.
- `config/settings.py:279` — `USE_I18N = True` existe pero
  **no hay** `LOCALE_PATHS`.
- `config/settings.py:166-177` — El `MIDDLEWARE` list **no incluye**
  `LocaleMiddleware`. El orden correcto en Django es:
  `SessionMiddleware` → `LocaleMiddleware` → `CommonMiddleware`;
  actualmente `SessionMiddleware` (índice 4) precede directamente a
  `CommonMiddleware` (índice 5).
- No existen directorios `locale/`, ni archivos `.po` ni `.mo`.
- Cero `{% load i18n %}` en templates; ningún language switcher.

Este cambio aborda la **infraestructura i18n completa** como primer slice
y traduce end-to-end la **app accounts** (el piloto) más las
**páginas públicas** citizen-facing (convocatorias, applications,
audit, claims). La justificación del piloto: la comunidad de revisión
puede validar el patrón sobre una app acotada antes de extenderlo al
resto de la plataforma.

### Decisiones de producto tomadas (no se discuten)

1. **Alcance del slice 1**: infraestructura i18n completa + app accounts
   traducida end-to-end + páginas públicas
   (~40 archivos: convocatories 3, applications 11, audit 4,
   claims públicos ~7, accounts ~14). El resto (governance, treasury,
   legalization, scoring, claims admin) queda para slices futuros.
2. **Idiomas del slice 1**: `es-CO` (default, msgids = español actual)
   + `en` (inglés). **Creole queda fuera** como decisión abierta
   documentada: solo `roadmap.md:437` lo menciona; `project.md`
   no lo exige como idioma de UI (el "trilingüismo" de
   `project.md:234` es un Área Académica Prioritaria, no i18n);
   se documenta en Fuera del alcance con los puntos pendientes.
3. **Documentos legales PDF excluidos**: pagaré, contrato, carta de
   instrucciones, actos administrativos (`templates/governance/`,
   `templates/legalization/pdf/*`) son instrumentos formales en
   español y no se traducen en este slice ni en slices futuros.
4. **Estrategia .mo**: `gettext` (xgettext/msgfmt) **no está
   disponible** en el entorno de desarrollo. Los `.po` se escriben
   a mano y se compilan vía **polib** (pure-Python, dev-dependency
   nueva) con `scripts/compile_mo.py`. Los `.mo` resultantes se
   commitean al repo. Los msgids son el texto español actual, con lo
   cual `es-CO` no requiere `.mo` y los tests existentes que assertan
   texto español no se rompen (es-CO sin .mo → fallback a msgid).

## Capacidades afectadas

- **CAP-030** — Multidioma y Trilingüismo (primaria)
- **Nota sobre mapeo**: `AGENTS.md §5` lista CAP-030 → `apps/accounts/`
  como dueño conceptual. El trabajo de este slice aterriza
  principalmente en `config/settings.py`, `templates/base.html`,
  `locale/` y los templates de accounts/convocatories/applications/
  audit/claims; accounts es la **app piloto** del primer slice.

## Reglas de negocio afectadas

- `project.md §5.1` — "Mensajes de UI: en **español**." Esta regla se
  interpreta como: **español es el idioma base** de la plataforma
  (msgids); el inglés es una traducción disponible. La regla NO se
  opone a un idioma adicional; la regla base (español) se preserva.
- **Ninguna norma citada**: ningún decreto, ley u Ordenanza del
  proyecto obliga el creole como idioma de UI. El trilingüismo de
  `project.md:234` es un área académica prioritaria (educación
  formal), no una exigencia de i18n. Se documenta en Fuera del alcance.

## Cambios propuestos

### 1. Settings (`config/settings.py`)

- Agregar `LANGUAGES = [("es-CO", "Español"), ("en", "English")]`.
- Agregar `LOCALE_PATHS = [BASE_DIR / "locale"]`.
- Insertar `"django.middleware.locale.LocaleMiddleware"` en
  `MIDDLEWARE` **después de** `SessionMiddleware` (índice 4) y
  **antes de** `CommonMiddleware` (índice 5), desplazando esta última
  a índice 6.

### 2. Infraestructura locale

- `locale/es_CO/LC_MESSAGES/django.po` — esqueleto vacío o mínimo;
  los msgids ya son español, no requiere traducciones activas.
- `locale/en/LC_MESSAGES/django.po` — traducciones del slice (todos
  los strings marcados en accounts, páginas públicas).
- `scripts/compile_mo.py` — script pure-Python que usa **polib** para
  compilar todos los `.po` → `.mo` recursivamente en `locale/`.
- `pyproject.toml` → agregar `polib` a `[project.optional-dependencies]
  dev`.
- Los `.mo` compilados se commitean al repo (no se generan en el
  contenedor de CI).

### 3. Base y switcher (`templates/base.html`)

- `{% load i18n %}` al inicio del archivo.
- Atributo `lang="{% get_current_language %}"` en `<html>`.
- Formulario switcher con `{% csrf_token %}` que hace POST a
  `{% url 'set_language' %}` (vista estándar de `django.views.i18n`);
  dos botones/links: "Español" y "English".
- Navbar y footer con `{% trans "texto" %}` para textos hardcoded.
- Los strings de los blocks `{% block %}` que se heredan (título de
  página, mensajes de error/success) se procesan vía trans si están
  hardcoded en el base o en los templates hijos.

### 4. App Accounts piloto (marcado de templates + traducciones)

Templates a marcar con `{% trans "..." %}` o `{% blocktrans %}...{%
  endblocktrans %}`:

`apps/accounts/templates/accounts/`:
- `login.html`, `register.html`, `profile.html`, `dashboard.html`
- `password_reset.html`, `password_reset_done.html`
- `password_reset_confirm.html`, `password_reset_complete.html`
- `partials/login_success.html`

No se toca `apps/accounts/templates/accounts/admin/` (admin fuera
del alcance de este slice).

Los `.po` resultantes registran los msgids (español actual) y sus
equivalentes en inglés.

### 5. Páginas públicas (marcado de templates)

**Convocatorias** (`templates/convocatories/`):
`index.html`, `detail.html`, `form.html` (3).

**Applications** (`templates/applications/`):
`wizard.html`; `partials/wizard_step_1.html` a `partials/wizard_step_5.html`;
`list.html`, `detail.html`; `review/list.html`, `review/detail.html`,
`review/history.html` (11).

**Audit** (`templates/audit/`):
`base.html`, `index.html`, `detail.html`, `verify.html` (4).

**Claims — plantillas públicas** (determinadas por análisis de
`apps/claims/views.py`: `LoginRequiredMixin` sin restricción de rol):
`claims/create.html`, `claims/list.html`, `claims/detail.html`,
`claims/edit.html`, `claims/apelacion_create.html`,
`claims/apelacion_list.html`, `claims/apelacion_detail.html` (7).
**Excluidos**: `claims/admin/list.html`, `claims/apelacion_admin_list.html`
(admin OFIJUR/Junta).

### 6. Exclusión explícita

Los documentos legales en PDF:
- `templates/governance/acto_pdf.html`
- `templates/legalization/pdf/*`
Permanecen exclusivamente en español. No se marcan con `{% trans %}`.

## Criterios de aceptación

- [ ] `settings.py` declara `LANGUAGES` con `es-CO` y `en`, y
      `LOCALE_PATHS` apunta a `BASE_DIR / "locale"`.
- [ ] `LocaleMiddleware` está en `MIDDLEWARE` entre
      `SessionMiddleware` y `CommonMiddleware`.
- [ ] El switcher de idioma en `base.html` hace POST a `set_language`
      y cambia el cookie `django_language`.
- [ ] Con cookie `en`, la página de login muestra títulos/enlaces en
      inglés (assertContains en test).
- [ ] Con cookie `es-CO` (o sin cookie, fallback), el HTML renderizado
      de las páginas tocadas es **byte-idéntico** al actual (regresión
      cero visual); los tests existentes de accounts pasan sin cambios.
- [ ] Los PDFs legales (`templates/governance/`, `templates/legalization/pdf/`)
      permanecen sin marcas `{% trans %}`.
- [ ] `scripts/compile_mo.py` compila todos los `.po` → `.mo`
      sin errores; los `.mo` se generan junto a sus `.po`.
- [ ] Los `.mo` commiteados se regeneran idempotentemente desde los
      `.po` del slice.
- [ ] Los `.po` en (`locale/en/LC_MESSAGES/django.po`) tienen
      entrada `msgstr` para todos los msgids marcados del slice.
- [ ] Suite completa verde en sqlite; PostgreSQL vía CI.
- [ ] `manage.py check` limpio.

## Pruebas

### Unitarias

- **Settings**: `LANGUAGES` contiene `es-CO` y `en`; `LOCALE_PATHS`
  resuelto; `LocaleMiddleware` presente en `MIDDLEWARE` y en la
  posición correcta (índice entre Session y Common).
- **Fallback es-CO**: test que verifica que con `LANGUAGE_CODE="es-CO"`
  y sin `.mo` para `es_CO`, Django retorna el msgid (texto español
  actual). Ejecutar GET `/accounts/login/` con `django_language=es-CO`
  y assert que el HTML contiene "Iniciar sesión" (msgid sin traducir).
- **compile_mo.py**: script genera los `.mo` desde los `.po` del slice
  sin excepciones; cada `.mo` contiene al menos un msgid verificado.

### Integración

- **Switcher → cookie**: POST a `set_language` con `language=en` →
  respuesta 302 + header `Set-Cookie` con `django_language=en`.
- **Login en inglés**: GET `/accounts/login/` con cookie `en` →
  `assertContains(response, "Login")` / `assertContains(response,
  "Register")` (o sus equivalentes en el template).
- **Regresión es-CO**: GET `/accounts/login/` sin cookie →
  `assertContains(response, "Iniciar sesión")`,
  `assertContains(response, "Registrarse")`; assert byte-identical
  al snapshot actual.

### Regresión

- Tests existentes en `apps/accounts/tests/` pasan sin modificación
  (mitigación: msgids = texto español literal → es-CO sin .mo →
  fallback a msgid = texto original → `assertContains` pasa).
- Tests de texto español en `apps/accounts/tests/test_validators.py`
  (`"al menos 8 caracteres"`, `"letra mayúscula"`, etc.) unaffected:
  esos strings viven en validators de Python, no en templates.

## Riesgos y Fuera del alcance

### Fuera del alcance

- **Creole como idioma de UI**: decisión abierta documentada.
  Puntos pendientes antes de incluirlo: código ISO 639-3,
  convención de ortografía, dotación de traducciones completa,
  verificación con hablantes nativos. Roadmap (`roadmap.md:437`)
  lo nombra como aspiración; `project.md §8` no lo exige.
- **Documentos legales PDF**: `templates/governance/`,
  `templates/legalization/pdf/`, pagaré, contrato, carta de
  instrucciones — permanecen en español.
- **API error messages DRF**: `reporting/views.py:34,36,42`,
  `legalization/views.py:103` — texto español hardcoded en respuestas
  JSON; fuera del piloto; deuda técnica documentada.
- **Templates internos restantes**: governance UI, treasury, legalization
  (no-PDF), scoring, claims admin (OFIJUR/Junta).
- **TextChoices raw labels** en `treasury/models.py:13` y
  `academic_tracking/models.py:11-12` — deuda técnica conocida;
  no se tocan en este slice.
- **Makemessages automation**: los `.po` se mantienen a mano en este
  slice. `gettext` (xgettext/msgfmt) no disponible en dev;
  mejora futura: agregar `gettext` al entorno y un workflow
  `django-admin makemessages` en CI.

### Riesgos

1. **Texto español hardcoded restante**: en templates no tocados
   (governance, treasury, legalization, scoring, claims admin).
   Los slices futuros de cada app deben marcar progresivamente.
   **Mitigación**: cada slice futur doc debe listar los archivos
   restantes por app.
2. **Mantenimiento bilingüe a mano de los .po**: sin makemessages
   es fácil que se quede un string sin traducir. **Mitigación**:
   script `compile_mo.py` con validación (`msgid` → `msgstr` presente);
   convención documentada en `docs/i18n-workflow.md` (futuro);
   gettext en CI como upgrade.
3. **Fragilidad de tests si se cambia un msgid**: un test que asserta
   texto exacto y un desarrollador que cambia el msgid rompe el test
   sin immediately obvious cause. **Mitigación**: msgids = texto
   actual literal (coincide con lo que el test verifica); documentar
   la convención en la guía de estilo del equipo.
4. **LocaleMiddleware en posición incorrecta**: si alguien reinserta
   `LocaleMiddleware` en la posición wrong, el language cookie no
   funciona. **Mitigación**: test de posición en la suite settings;
   comentario exacto en `settings.py` indicando la posición.
5. **Interpolación con variables**: strings con `{{ variable }}` o
   `%(name)s` requieren `{% blocktrans %}...{% endblocktrans %}` en
   templates y `% (name)s` en Python. **Mitigación**: en el piloto
   accounts/convocatories/applications/audit/claims el número de
   interpolaciones es bajo; se usan las formas correctas desde el
   inicio.
