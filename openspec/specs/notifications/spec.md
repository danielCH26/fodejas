# Notifications — Spec (CAP-019)

## Purpose

Notificaciones **in-app** para FODEJAS (CAP-019). Habilita la
bandeja que consume CHG-105 (`habeas.*`) y el criterio de salida
Fase 1. Sin email/SMS/push en MVP; el puerto abstracto permite
cambiar de canal sin acoplar consumidores.

## ADDED Requirements

### Requirement: Notification Model

`accounts.Notification` SHALL tener: `id` UUID PK; `recipient`
FK `accounts.User` (CASCADE); `event` `CharField(64)` (código
estable); `tipo` `CharField(16)` ∈
`info|warning|success|error`; `titulo` `CharField(140)`;
`mensaje` `TextField` (PII enmascarada); `payload` `JSONField`
saneado; `leido` `BooleanField` derivado de `read_at`;
`read_at` `DateTimeField` nullable; `created_at` UTC auto.
Índice SHALL ser `(recipient, read_at, created_at DESC)`.

#### Scenario: Creación desde servicio

- GIVEN `NotificationPort.notify(user, "habeas.created", payload_masked)`
- WHEN `InAppNotifier.notify(...)` persiste
- THEN existe `Notification(recipient=user, event="habeas.created", leido=False)`

#### Scenario: PII enmascarada

- GIVEN `payload` con `documento`/`telefono`/`email`
- WHEN se persiste
- THEN el JSON guardado contiene valores enmascarados (`***123`); `audit` emite `notification.created`

#### Scenario: Idempotencia diaria

- GIVEN dos `notify()` con mismo `(recipient, event)` mismo día UTC
- WHEN el segundo ejecuta
- THEN no crea duplicado; `payload.repeat_count` se incrementa

### Requirement: NotificationPort Abstracto

`NotificationPort(Protocol)` SHALL exponer
`notify(user, event, payload_masked) -> Notification` y
`mark_read(notification, user) -> None`. Consumidores SHALL
depender solo del port. Binding SHALL ocurrir en
`apps.py::ready()` (`InAppNotifier` por defecto).

#### Scenario: Despacho a múltiples adapters

- GIVEN port con `[InAppNotifier, X]`
- WHEN `notify(...)` ejecuta
- THEN cada adapter es invocado

#### Scenario: Reemplazo del NoopNotifier

- GIVEN `apps.py.ready()` con `InAppNotifier`
- WHEN un consumidor llama `NotificationPort.notify(...)`
- THEN delega a `InAppNotifier` (no a `NoopNotifier`)

### Requirement: InAppNotifier

`InAppNotifier` SHALL (1) enmascarar `payload` vía
`apps.core.logging.mask_pii` (CHG-103), (2) upsert `Notification`
transaccional, (3) encolar `dispatch_notification.delay(id)`, (4)
emitir `notification.created` a `audit`.

#### Scenario: Encolado no bloqueante

- GIVEN request HTTP invocando `notify(...)`
- WHEN la vista retorna
- THEN la `Notification` ya está persistida; el envío asíncrono ocurre fuera

#### Scenario: Falla de broker no rompe creación

- GIVEN Redis no disponible al encolar
- WHEN `delay()` lanza `ConnectionError`
- THEN la `Notification` queda creada y `audit` emite `notification.dispatch_failed`

### Requirement: API REST (DRF + JWT, scope=owner)

- `GET /api/notifications/` SHALL lista paginada del `request.user`
  (default 20, max 100); filtros `?leido=true|false`.
- `POST /api/notifications/{id}/read/` SHALL marca `read_at=now()`
  si pertenece al usuario.
- `POST /api/notifications/read-all/` SHALL marca todas las
  pendientes.
- `403` SHALL si no pertenece al `request.user`.

#### Scenario: Listado paginado del propio usuario

- GIVEN usuario A con 25 notificaciones
- WHEN GET `/api/notifications/?page=2`
- THEN retorna 5 items propios; nunca de otros usuarios

#### Scenario: Marcar leída

- GIVEN notificación N del usuario A, `leido=False`
- WHEN POST `/api/notifications/{N.id}/read/`
- THEN `N.read_at` se setea; `200` con `read_at`

#### Scenario: read-all idempotente

- GIVEN usuario A con 10 pendientes
- WHEN POST `/api/notifications/read-all/` dos veces
- THEN la segunda retorna `{updated: 0}`

#### Scenario: Notificación ajena

- GIVEN usuario A intenta `read/` sobre N de usuario B
- WHEN ejecuta
- THEN `403` y `audit` emite `notification.access_denied`

#### Scenario: Sin autenticación

- GIVEN request sin token
- WHEN GET `/api/notifications/`
- THEN `401`

### Requirement: Admin Django

`/admin/accounts/notification/` SHALL restringirse a
**R-ADMIN / R-COORD** (CAP-001). Lista SHALL mostrar
`recipient`, `event`, `tipo`, `leido`, `created_at` con filtros
`tipo`/`event`/`leido`/fecha. Acciones SHALL: `marcar_como_leida`
y `reenviar_a_audit`.

#### Scenario: Marcar masivo desde admin

- GIVEN R-ADMIN selecciona 50 notificaciones no leídas
- WHEN aplica `marcar_como_leida`
- THEN todas quedan `leido=True` con `read_at=now()`; `audit` registra lote

#### Scenario: R-CT bloqueado

- GIVEN R-CT en `/admin/accounts/notification/`
- WHEN navega
- THEN `403` y `audit` emite `permission_denied`

### Requirement: Celery `dispatch_notification`

`@shared_task dispatch_notification(notification_id)` SHALL ser
**idempotente**: si `dispatched_at` ya está set, retorna sin
duplicar. Cada ejecución SHALL emitir `notification.dispatched`
a `audit`. Retries SHALL usar backoff exponencial (3 intentos).

#### Scenario: Idempotencia

- GIVEN `Notification` ya con `dispatched_at`
- WHEN Celery la re-ejecuta
- THEN retorna sin re-emitir audit ni side-effects

#### Scenario: Reintento con backoff

- GIVEN `audit.emit()` lanza `TransientError` en intento 1
- WHEN el task reintenta
- THEN intento 2 ocurre tras backoff; tras 3 fallos queda `FAILED` con `notification.dispatch_failed`