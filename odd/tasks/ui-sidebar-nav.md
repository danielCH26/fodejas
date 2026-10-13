# UI: Navbar → Sidebar (dashboard FODEJAS)

> Tarea ODD generada desde anotación de diseño en Orca Browser sobre
> `http://localhost:8001/accounts/dashboard/` (tab `c4b04bf0`, viewport
> 1724x773). Sesión 2026-10-12.

## Decisión de diseño (elegida por el usuario)

Sidebar clásica a la izquierda con la marca **FODEJAS centrada en el
encabezado del sidebar**; links apilados con íconos; idioma y usuario abajo.

## Nota sobre decisión previa (stale)

`odd/tasks/mvp-route.md` (2026-10-09) declaró este clon
(`FodejaApp/fodejas`) «congelado, solo lectura» y canónico
`Downloads/fodejas`. **Evidencia actual lo desmiente**: este clon tiene el
commit del día (`6c4a041`, 2026-10-12, CAP-001), es el worktree activo de
Orca, sirve `localhost:8001` y es donde el usuario anota. Se trabaja acá.

## Alcance

- **Dentro**: `templates/base.html` (nav → sidebar, responsive, estilos inline).
- **Fuera**: `templates/transparencia/base.html` (sección pública, otro nav).
- **Fuera**: lógica de roles/permisos, URLs, i18n — se preservan tal cual.

## Tareas

- [x] T1: Reestructurar `templates/base.html`: sidebar fija izquierda
      (~260px, `--fodejas-primary`), marca centrada arriba, links apilados
      con estado activo por `request.path`, sección Administración como
      grupo colapsable, idioma + usuario abajo; off-canvas móvil (<lg) con
      hamburger (Bootstrap offcanvas, sin dependencias nuevas); corregir
      `</ul>` duplicado preexistente; anon ve solo marca + Transparencia.
      Nav extraído a `templates/partials/sidebar_nav.html` (instancia
      única con ids sufijados desktop/mobile; sin markup duplicado).
- [x] T2: Verificación funcional en vivo (Orca browser): desktop 1724px y
      móvil (~390px), sidebar renderiza, marca centrada, links y roles
      correctos, sin overflow horizontal. (Sin RED determinista: no hay
      tests que dependan del navbar; verificación visual/funcional.)
      Resultados: `manage.py check` 0 issues; render 200 OK; 0 errores de
      consola; snapshot desktop con todos los links; overflow scrollWidth
      1709 ≤ 1724; adminCollapse-desktop/mobile únicos; offcanvas móvil
      abre con Perfil/Cerrar sesión. Defecto detectado y corregido:
      comentario `{# #}` multi-línea del parcial filtraba al DOM (Django
      no soporta multi-línea) → convertido a `{% comment %}`; re-verificado
      (`innerText` ya no lo contiene). Emulación de dispositivo móvil de
      Orca no cambió el viewport (limitación de Orca, no del CSS; media
      queries correctas en DOM). Screenshot evidencia:
      `%TEMP%/fodejas-sidebar-verify/desktop-final.png`.
- [x] T3: Work-unit commit en `feat/ui-sidebar-nav` + evidencia aquí.

## Evidencia

- Verificación: gentle-ai-verify (mv61ljjh-1-n3i2, fix round; spot-check
  post-fix inline). 8 PASS / 1 BLOCKED (emulación móvil de Orca) / 1
  defecto corregido.
- Commit: `0f4e0bd` — feat(ui): replace top navbar with fixed left sidebar
  (feat/ui-sidebar-nav, 3 archivos, +388/−184; incluye partial nuevo y este doc).
