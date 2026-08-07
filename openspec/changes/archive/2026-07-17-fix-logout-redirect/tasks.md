# Tasks - Fix Logout Redirect

## 1. Corregir LogoutView ✅

- [x] Modificar `apps/accounts/accounts_views.py` - clase `LogoutView`
  - Cambiar herencias de `BaseLogoutView` a `LogoutView` de Django
  - Simplificar `dispatch` para solo agregar mensaje

## 2. Corregir Dashboard Navigation URLs ✅

- [x] Modificar `apps/accounts/accounts_views.py` - método `_get_navigation_items`
  - Cambiar `/api/applications/solicitudes/` a `/applications/` para todos los roles
  - Actualizar `/api/treasury/pagos/` a `/convocatorias/` para R-TESORERO

## 3. Tests

- [ ] Ejecutar tests existentes: `pytest apps/accounts/tests/test_views.py::LogoutViewTests -v`
- [ ] Verificar que no hay regressions en otros tests de accounts

## 4. Validación Manual

- [x] Probar logout desde el dashboard
- [x] Verificar redirección correcta
- [x] Verificar mensaje de éxito
- [x] Verificar que páginas protegidas requieren login
- [x] Verificar navegación del dashboard funciona
