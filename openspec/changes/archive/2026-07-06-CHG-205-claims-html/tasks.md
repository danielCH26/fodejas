# Tasks — CHG-205 Interfaz HTML para Reclamaciones

## 1. Modelos

- [x] 1.1 Crear modelo `Reclamacion` en `apps/claims/models.py`
- [x] 1.2 Crear modelo `ReclamacionHistorial`
- [x] 1.3 Crear migración Django
- [x] 1.4 Ejecutar migración
- [x] 1.5 Registrar en admin.py

## 2. Servicio de Reclamaciones

- [x] 2.1 Crear `apps/claims/services/__init__.py`
- [x] 2.2 Implementar `crear_reclamacion()`
- [x] 2.3 Implementar `cambiar_estado()` con transiciones
- [x] 2.4 Implementar `resolver_reclamacion()`
- [x] 2.5 Implementar transiciones válidas

## 3. Vistas

- [x] 3.1 Crear `ReclamacionCreateView`
- [x] 3.2 Crear `ReclamacionListView` (usuario)
- [x] 3.3 Crear `ReclamacionDetailView`
- [x] 3.4 Crear `ReclamacionUpdateView`
- [x] 3.5 Crear `ReclamacionAdminListView` (Junta)
- [x] 3.6 Crear `ReclamacionResolveView`
- [x] 3.7 Agregar permisos por rol

## 4. URLs

- [x] 4.1 Configurar `apps/claims/urls.py` con UUID
- [x] 4.2 Incluir en `config/urls.py`

## 5. Templates

- [x] 5.1 Crear `templates/claims/create.html`
- [x] 5.2 Crear `templates/claims/list.html`
- [x] 5.3 Crear `templates/claims/detail.html`
- [x] 5.4 Crear `templates/claims/edit.html`
- [x] 5.5 Crear `templates/claims/admin/list.html`

## 6. Integración

- [ ] 6.1 Agregar botón "Presentar Reclamación" en CHG-204 (ranking)
- [ ] 6.2 Integrar notificaciones (CAP-019)
- [ ] 6.3 Verificar auditoría (CAP-022)

## 7. Pruebas

- [ ] 7.1 Tests unitarios para modelo
- [ ] 7.2 Tests para views
- [ ] 7.3 Tests de flujo: crear → resolver
- [ ] 7.4 Tests de permisos

## 8. Verificación

- [x] 8.1 Django check pasa
- [ ] 8.2 Acceso como aspirante crea reclamación
- [ ] 8.3 Acceso como Junta resuelve reclamación
- [x] 8.4 UUID en URLs
- [ ] 8.5 Notificaciones enviadas
- [x] 8.6 Historial de cambios

## Estado

- 🔄 En progreso (modelos, servicios, vistas, templates completados)
- Pendiente: integración con scoring, notificaciones, tests

## Notas

- Dependencias: CHG-202, CHG-204
- Siguiente: CHG-206 (Apelaciones 2ª instancia)
