# Feature: Dashboard notifications + recent activity (bugfix)

> Bug report (usuario): en `http://localhost:8001/accounts/dashboard/`
> las **notificaciones** y las **acciones recientes** no funcionan.
>
> Causa raíz encontrada: `apps/accounts/templates/accounts/dashboard.html`
> tiene las secciones "Actividad Reciente" y "Notificaciones" como
> **placeholders estáticos** (siempre muestran "No hay actividad" /
> "No tiene notificaciones"), y `DashboardView.get_context_data`
> nunca consulta `Notification` ni `AuditEvent`.
> El modelo `Notification` y `InAppNotifier` sí funcionan
> (application views y habeas API crean notificaciones), pero el
> dashboard no las muestra.

## Tareas

1. **Tests primero (RED)** — `apps/accounts/tests/test_views.py`:
   - [x] 1.1 `test_dashboard_shows_user_notifications` — crea Notification
     para el usuario, assertContains del título
   - [x] 1.2 `test_dashboard_excludes_other_users_notifications` —
     notificación de otro usuario no aparece
   - [x] 1.3 `test_dashboard_shows_recent_activity` — crea AuditEvent vía
     `log_audit_event`, assertContains de la entidad
   - [x] 1.4 `test_dashboard_excludes_other_users_activity` — evento de
     otro actor no aparece
2. **Vista (GREEN)** — `apps/accounts/accounts_views.py` DashboardView:
   - [x] 2.1 context `notifications` (últimas 10 del usuario)
   - [x] 2.2 context `unread_count`
   - [x] 2.3 context `recent_events` (últimos 10 AuditEvent del actor)
3. **Template** — `apps/accounts/templates/accounts/dashboard.html`:
   - [x] 3.1 sección Notificaciones: lista real con badge por tipo,
     resaltado de no leídas, contador, mensaje y fecha; placeholder
     solo si no hay datos
   - [x] 3.2 sección Actividad Reciente: lista real (acción, entidad,
     fecha); placeholder solo si no hay datos
4. **Verificación y commit**
   - [x] 4.1 suite de apps/accounts + apps/audit en verde
   - [x] 4.2 work-unit commit en rama `fix/dashboard-notifications`

## Hallazgos adicionales

- El ítem de menú "Mis Notificaciones" apunta a `/accounts/notifications/`
  pero **esa ruta no existe** (404) — `apps/accounts/urls.py` no la define.
  Fuera del alcance de este fix (el dashboard ahora muestra las
  notificaciones inline); pendiente decisión de usuario: crear la
  página de listado o quitar el ítem.
- Strings nuevos en el template (`Nueva`, badges de tipo) pueden
  requerir entrada en el catálogo i18n en la próxima pasada CAP-030.

## Evidencia

- RED observado: 4 tests nuevos fallando, 5 previos pasando.
- GREEN: DashboardViewTests 9/9; suite apps/accounts + apps/audit
  172 passed, 2 skipped (skips pre-existentes de django-storages).
