# Fix Logout Redirect - Spec

## Requisitos Funcionales

### RF-001: Logout redirecciona correctamente

**Descripción**: Cuando un usuario autenticado accede a `/accounts/logout/`, debe ser redirigido a la página de login (`/accounts/login/`) después de cerrar la sesión.

**Criterios**:
- La sesión del usuario debe ser destruida
- El usuario no debe poder acceder a páginas autenticadas sin volver a login
- La redirección debe ser absoluta (`/accounts/login/`), no relativa

### RF-002: Mensaje de éxito mostrado

**Descripción**: Después de un logout exitoso, debe mostrarse un mensaje indicando que la sesión fue cerrada.

**Criterios**:
- El mensaje "Sesión cerrada correctamente." debe aparecer en la página de login después del logout
- El mensaje debe ser de tipo success (no error)

### RF-003: Dashboard navigation URLs correctas

**Descripción**: Las URLs de navegación en el dashboard deben apuntar a las rutas HTML correctas, no a las APIs eliminadas.

**Criterios**:
- Aspirante: `/applications/` en lugar de `/api/applications/solicitudes/`
- Revisor: `/applications/` en lugar de `/api/applications/solicitudes/`
- Comité: `/applications/` en lugar de `/api/applications/solicitudes/`
- Coordinador: `/applications/` en lugar de `/api/applications/solicitudes/`
- Admin: `/applications/` en lugar de `/api/applications/solicitudes/`
- Tesorero: No hay ruta HTML para pagos todavía (dejar como placeholder)

## Escenarios

### Escenario 1: Usuario cierra sesión

**Dado** que el usuario está autenticado
**Cuando** accede a `/accounts/logout/` vía POST
**Entonces** la sesión se cierra y es redirigido a `/accounts/login/`
**Y** al intentar acceder a `/accounts/dashboard/` es redirigido a login

### Escenario 2: Usuario no autenticado accede a logout

**Dado** que el usuario NO está autenticado
**Cuando** accede a `/accounts/logout/`
**Entonces** es redirigido directamente a `/accounts/login/`

### Escenario 3: Dashboard muestra navegación correcta

**Dado** que el usuario tiene rol R-ASPIRANTE
**Cuando** accede al dashboard
**Entonces** ve el enlace "Mis Postulaciones" apuntando a `/applications/`

## Notas de Implementación

- Usar `LogoutView` de Django directamente con `next_page = 'login'`
- Agregar mixin de messages para mostrar éxito
- Las URLs del dashboard están en `_get_navigation_items` de `DashboardView`
