# Fix Logout Redirect - Propuesta

## Contexto

El método `LogoutView` en `apps/accounts/accounts_views.py` no está funcionando correctamente para ningún tipo de usuario. La implementación actual tiene dos problemas:

1. **LogoutView duplica logout**: Llama `logout(request)` manualmente y luego `super().dispatch()` que también hace logout, causando comportamiento inconsistente.

2. **Dashboard usa URLs de API eliminadas**: La navegación del dashboard ссылается a URLs de API que fueron eliminadas (`/api/applications/solicitudes/`, `/api/treasury/pagos/`).

## Problema Específico

La implementación actual:
```python
class LogoutView(BaseLogoutView):
    next_page = "login"

    def dispatch(self, request, *args, **kwargs):
        logout(request)  # Primera llamada
        messages.success(request, "Sesión cerrada correctamente.")
        return super().dispatch(request, *args, **kwargs)  # Segunda llamada (redundante)
```

El `BaseLogoutView` de Django ya hace logout en su `dispatch`, por lo que hay redundancia y posible conflicto con el manejo de mensajes.

## Reglas de Negocio Afectadas

- Ninguna regla de negocio afectada directamente.

## Cambios Propuestos

1. **Corregir LogoutView**: Simplificar la implementación para usar solo la lógica del padre, agregando solo el mensaje de éxito.

2. **Corregir DashboardView**: Actualizar las URLs de navegación para usar las rutas HTML correctas en lugar de las APIs eliminadas.

## Criterios de Aceptación

- [ ] El logout redirige correctamente a /accounts/login/
- [ ] El mensaje "Sesión cerrada correctamente" se muestra
- [ ] Después de logout, acceder a páginas protegidas redirige al login
- [ ] Las URLs de navegación del dashboard funcionan correctamente
- [ ] Los tests existentes pasan

## Pruebas

- Ejecutar tests existentes de LogoutView: `pytest apps/accounts/tests/test_views.py::LogoutViewTests`
- Verificar manualmente el flujo de logout con diferentes usuarios

## Riesgos y Outside Scope

- **Riesgos**: Bajo - solo se corrige código existente
- **Outside Scope**: No se implementan nuevas funcionalidades, solo se corrige el bug de redirect y se actualizan URLs obsoletas.
