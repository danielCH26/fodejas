# Fix Logout Redirect - Design

## Arquitectura

### Componentes Affected

| Componente | Tipo | Cambio |
|------------|------|--------|
| `apps/accounts/accounts_views.py` | View | Modificar `LogoutView` y `DashboardView._get_navigation_items` |
| `apps/accounts/tests/test_views.py` | Test | Verificar que tests existentes pasan |

## Cambios de Código

### 1. LogoutView Corregido

**Archivo**: `apps/accounts/accounts_views.py`

**Antes**:
```python
class LogoutView(BaseLogoutView):
    next_page = "login"

    def dispatch(self, request, *args, **kwargs):
        logout(request)
        messages.success(request, "Sesión cerrada correctamente.")
        return super().dispatch(request, *args, **kwargs)
```

**Después**:
```python
class LogoutView(LogoutView):
    """Logout view with success message."""
    next_page = "login"
    template_name = "accounts/logged_out.html"

    def dispatch(self, request, *args, **kwargs):
        messages.success(request, "Sesión cerrada correctamente.")
        return super().dispatch(request, *args, **kwargs)
```

**Nota**: Usar `django.contrib.auth.views.LogoutView` directamente, no el `BaseLogoutView`. La clase base de Django maneja el logout correctamente.

### 2. Dashboard Navigation URLs

**Archivo**: `apps/accounts/accounts_views.py`, método `_get_navigation_items`

**Cambios de URLs**:

| Rol | URL Anterior | URL Nueva |
|-----|--------------|----------|
| R-ASPIRANTE | `/api/applications/solicitudes/` | `/applications/` |
| R-REVISOR | `/api/applications/solicitudes/` | `/applications/` |
| R-COMITE | `/api/applications/solicitudes/` | `/applications/` |
| R-COORDINADOR | `/api/applications/solicitudes/` | `/applications/` |
| R-ADMIN | `/api/applications/solicitudes/` | `/applications/` |
| R-TESORERO | `/api/treasury/pagos/` | `/convocatorias/` (placeholder) |

## Testing

### Tests Existentes a Ejecutar

```bash
pytest apps/accounts/tests/test_views.py::LogoutViewTests -v
```

### Tests Esperados

| Test | Estado Esperado |
|------|----------------|
| test_logout_redirects_to_login | PASS |
| test_logout_clears_session | PASS |

## Validación Post-Fix

1. Login como usuario
2. Ir a `/accounts/logout/`
3. Verificar redirección a `/accounts/login/`
4. Verificar mensaje de éxito
5. Intentar acceder a `/accounts/dashboard/` - debe redirigir a login
