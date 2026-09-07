# CHG-801 — Reparar cadena de auditoría CAP-022 (hash chain + signals + permisos de lectura)

> **Convención de numeración**: este change extiende la numeración más
> allá del rango `CHG-5xx` (Fase 5) hacia `CHG-8xx` reservado para
> cambios **transversales de remediación** que tocan capacidades de
> múltiples fases. Justificación: AGENTS.md §14 no define rango para
> fixes que cruzan fases; un rango dedicado evita colisiones futuras
> con CHG-501..507.

## Contexto

La auditoría completa del 2026-09-05 (`docs/audits/initial-audit.md`
AUD-001..003, AUD-010, AUD-015, AUD-020 y `docs/audits/extended-audit.md`
reclasificaciones) detectó que la cadena de auditoría de CAP-022 está
rota en **todas las capas**:

- **Modelo** (`apps/audit/models.py:59-64`): `get_previous_hash()` no
  usa `select_for_update()`, race condition en escrituras concurrentes
  (AUD-003).
- **Servicios**: cinco call sites crean `AuditEvent` directamente con
  `AuditEvent.objects.create(...)` usando campos que no existen
  (`user=`, `details=`) o sin computar el hash, y cada uno está envuelto
  en `try/except Exception: pass` que se traga los errores (AUD-001 +
  AUD-020).
- **Signals** (`apps/audit/signals.py:62-67`): `AUDIT_MODELS` lista
  strings pero `sender` es una clase → el check siempre falla. La
  función `register_audit_signals()` está definida pero nunca se llama.
  Resultado: cero audit events automáticos (AUD-010, reclasificado a
  CRITICAL).
- **Atribución** (`apps/audit/signals.py:81-92` y `:104-112`): ambos
  handlers pasan `actor=None` porque no hay middleware que lea el
  usuario del request (AUD-002).
- **Permisos de lectura** (`apps/audit/views.py:11-16`):
  `AuditEventListView` requiere solo `IsAuthenticated`; un
  `R-ASPIRANTE` puede leer todo el log (AUD-015).

AGENTS.md §6 regla 1 ("trazabilidad inmutable desde el día 1") y
CAP-022 (project.md §9.3) están incumplidos en producción. Ningún ente
de control puede confiar en este log mientras esto siga así.

## Capacidades afectadas

- **CAP-022** (Bitácora inmutable con hash chain, `project.md` §8) —
  roto a nivel de modelo, signals, servicios y permisos.

## Reglas de negocio afectadas

- `AGENTS.md` §6 regla 1 (trazabilidad inmutable desde el día 1).
- `AGENTS.md` §6 regla 5 (no saltarse pruebas en transiciones de
  estado).
- `AGENTS.md` §6 regla 6 (lógica de auditoría en `services/`, no en
  vistas).
- `project.md` §9.3 (CAP-022 contrato: append-only con hash chain).

## Cambios propuestos

### Delta en `specs/audit/spec.md`

#### MODIFIED — §3 Auditoría append-only

El método canónico para escribir audit events pasa a ser
`apps.audit.services.log_audit_event(...)`. Los servicios de dominio
**SHALL NOT** llamar `AuditEvent.objects.create(...)` directamente.

El modelo `AuditEvent` **SHALL** computar `previous_hash` y
`current_hash` dentro de una transacción que tome `SELECT ... FOR
UPDATE` sobre la cabeza de la cadena.

`AuditConfig.ready()` **SHALL** invocar `register_audit_signals()` al
cargar la app, conectando `post_save` y `post_delete` por cada modelo
en `AUDIT_MODELS` (comparando `sender` contra clases, no strings).

`audit_save_receiver` y `audit_delete_receiver` **SHALL** leer el
usuario actual de `apps.core.middleware.RequestIDMiddleware` (o
extensión equivalente) y propagarlo como `actor=`. Cuando no haya
request (management command, signal fuera de flujo HTTP), el campo
`actor` puede ser `NULL`, pero esto **SHALL** registrarse con un
sentinel distinguible (`actor_is_system=True`) en metadata.

`AuditEventListView` **SHALL** exigir `IsAuditViewer` (ya existe en
`apps/accounts/permissions.py:230-248`) en lugar de `IsAuthenticated`.

### Cambios concretos

1. `apps/audit/services.py`:
   - Agregar `transaction.atomic` + `select_for_update()` alrededor de
     `get_previous_hash()` + creación del evento.
   - Hacer el helper tolerante a `actor=None` (con sentinel).
2. `apps/audit/models.py`: regla en `save()` que rechace escritura
   directa fuera de `services.log_audit_event` con `RuntimeError`
   cuando se llame desde otro contexto (`assert` removible en
   producción con flag de setting).
3. `apps/audit/signals.py`:
   - Reemplazar `AUDIT_MODELS` por tuplas `(ModelClass, "module")`
     en lugar de `(string, string)`.
   - Llamar `register_audit_signals()` desde `apps/audit/apps.py
     ready()`.
4. `apps/core/middleware.py`: extender `RequestIDMiddleware` (o crear
   `ActorMiddleware`) que guarde el usuario actual en
   `_request_var.actor` accesible desde signals.
5. `apps/legalization/signer.py:181-192`,
   `apps/accounts/services/notifications.py:185-194`,
   `apps/convocatories/services/convocatoria_service.py:166-178`,
   `apps/applications/services/wizard_service.py:109-118`: reemplazar
   cada `AuditEvent.objects.create(...)` por
   `log_audit_event(...)`. Eliminar los `try/except Exception: pass`
   que se tragan errores de auditoría.
6. `apps/audit/views.py:11-16`: cambiar
   `permission_classes = [IsAuditViewer]`.

## Criterios de aceptación

- [ ] `apps/audit/tests.py` incluye un test que crea 3 eventos
      consecutivos y verifica que `current_hash[N] == sha256(N-1,
      payload[N])` y que la cadena valida con `verify_chain()`.
- [ ] Test de concurrencia: 2 hilos lanzan 100 escrituras cada uno;
      todas pasan la validación final de cadena sin bifurcaciones.
- [ ] Test de signals: guardar un `Role` dispara un `AuditEvent` con
      `actor=<request user>` y `previous_hash` correcto.
- [ ] Test de signals: guardar un `Estrato` (catalog) dispara un
      `AuditEvent` con `module="core"`.
- [ ] Test de permisos: `R-ASPIRANTE` recibe 403 en
      `GET /api/audit/events/`.
- [ ] `pytest apps/audit/` corre limpio.
- [ ] Las 5 sites de `AuditEvent.objects.create(...)` desaparecen del
      `grep -r "AuditEvent.objects.create" apps/`.

## Pruebas

- Unitarias:
  - `apps/audit/tests/test_chain.py` — integridad del hash chain.
  - `apps/audit/tests/test_concurrency.py` — race conditions.
  - `apps/audit/tests/test_signals.py` — signals automáticos.
- Integración:
  - `apps/legalization/tests/test_signer.py` — verifica que firmar un
    documento escribe un audit event válido.
  - `apps/accounts/tests/test_notifications.py` — verifica que
    notificar escribe un audit event válido.
- Permisos:
  - `apps/audit/tests/test_views_permissions.py` — R-ASPIRANTE no
    puede leer el log.

## Riesgos y Fuera del alcance

- **Riesgo**: el cambio en `signals.py` puede activar muchos eventos
  donde antes no se generaban → crecimiento súbito de la tabla
  `audit_log`. Mitigación: agregar índice en
  `(entity, entity_id, timestamp)` y documentar política de retención.
- **Riesgo**: si `RequestIDMiddleware` no estaba siendo invocado en
  ciertos flujos (management commands, signals en cascada), el actor
  quedará `NULL`. Esto es aceptable solo si la metadata lleva el
  sentinel `actor_is_system=True`.
- **Fuera del alcance**:
  - No se rediseña el modelo de auditoría (no hay campos nuevos).
  - No se migran los audit events ya existentes (no hay datos
    productivos confirmados).
  - No se agrega rate-limiting sobre `audit/events/`.
  - Las correcciones de `apps/reporting/` y `apps/psychosocial/` van
    en otro change.

## Referencias

- `docs/audits/initial-audit.md` §3.2 AUD-001, AUD-002, AUD-003,
  §3.3 AUD-010 (reclasificado), §3.4 AUD-015.
- `docs/audits/extended-audit.md` §5.5 reclasificación AUD-010,
  §8.2 AUD-020.
- `AGENTS.md` §6 reglas 1, 5, 6.
