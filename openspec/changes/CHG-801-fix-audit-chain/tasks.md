# Tasks — CHG-801 Reparar cadena de auditoría CAP-022

> Plan de implementación derivado de
> `openspec/changes/CHG-801-fix-audit-chain/proposal.md`.
> Cada tarea lista subtareas verificables. Marcado progresivamente a
> medida que `sdd-apply` las completa.

## 1. Audit model + services (transactional safety, select_for_update)

- [x] `apps/audit/services.py::log_audit_event(...)` envuelve la lectura de
      `previous_hash` + `AuditEvent.objects.create(...)` dentro de un
      `transaction.atomic` y usa `AuditEvent.objects.select_for_update()
      .order_by("-timestamp").first()` para leer la cabeza de la cadena.
- [x] `apps/audit/models.py::AuditEvent.get_previous_hash()` permanece
      inalterado como helper; la versión con lock vive inline en
      `log_audit_event(...)` para no contaminar al modelo con semántica
      transaccional.
- [x] El helper sigue siendo **idempotente** desde la API pública:
      firma `(actor, action, entity, entity_id, changes=None,
      ip_address=None, user_agent=None, module=None) -> AuditEvent`.
- [x] Docstring de `log_audit_event(...)` documenta: (a) lock por
      `SELECT ... FOR UPDATE` sobre la cabeza, (b) tolerancia a
      `actor=None` con sentinel `actor_is_system=True`, (c) excepción
      `AuditChainError` si la cabeza de la cadena está corrupta.

## 2. Audit signals (AUDIT_MODELS como clases, register_audit_signals desde AppConfig)

- [x] `apps/audit/signals.py::AUDIT_MODELS` reemplaza las tuplas con
      strings por tuplas `(ModelClass, "module")`. Las clases se
      importan desde el registry de Django apps (`apps.core.models`
      `Estrato`, `GrupoSisben`, `Etnia`, `MunicipioIsla`,
      `NivelFormacion`, `ModalidadApoyo`, `TipoIes`, `TipoDocumento`,
      `EstadoDocumento`, `CausalTerminacionConvenio`,
      `apps.convocatories.models` `Convocatory`,
      `ConfiguracionConvocatoria`, `Hito`, `Cupo`,
      `ConvocatoriaVersion`).
- [x] `audit_save_receiver` y `audit_delete_receiver` comparan
      `sender` con `is`-equality contra `AUDIT_MODELS`
      (`not any(sender is m[0] for m in AUDIT_MODELS)`).
- [x] `apps/audit/signals.py` importa
      `apps.core.middleware.get_request_actor` (o equivalente del
      contextvar) y lo pasa como `actor=...` a `log_audit_event(...)`
      cuando haya un valor; si está vacío, `actor=None` y se marca
      `actor_is_system=True` en metadata.
- [x] Los `try/except Exception: pass` que se tragan los errores de
      auditoría se reemplazan por una llamada a
      `apps.core.logging_config.logger.exception(...)` para que la
      falla quede registrada sin abortar la operación principal.

## 3. Audit actor middleware (extender RequestIDMiddleware)

- [x] `apps/core/logging_config.py` añade un contextvar
      `actor_var: ContextVar[Any]` (model instance o `None`) con
      `set_actor(user)` y `get_actor()`. El contextvar se limpia al
      salir del request.
- [x] `apps/core/middleware.py::RequestIDMiddleware.__call__` setea
      `actor_var` con `request.user` cuando está autenticado
      (modelo completo, no sólo `id`); al salir del request,
      `actor_var.set(None)`.
- [x] Los handlers de auditoría leen `get_actor()` directamente desde
      `logging_config` (sin importar middleware), evitando ciclos de
      import.

## 4. Reemplazar 5 sites directos `AuditEvent.objects.create(...)`

- [x] `apps/legalization/signer.py::_log_signature_audit` usa
      `log_audit_event(...)` con `actor` (lookup por `actor_id`),
      `action="ELECTRONIC_SIGNATURE"`, `entity=document_type`,
      `module="legalization"`, payload vía kwarg soportado (p.ej.
      `changes={...}`). Eliminar el `try/except Exception: pass`.
- [x] `apps/accounts/services/notifications.py::_log_audit_event`
      reescrita como wrapper sobre `log_audit_event(...)` con
      `actor=user`, `module="accounts"`. Eliminar los dos
      `try/except Exception: pass` que se tragan errores.
- [x] `apps/convocatories/services/convocatoria_service.py::_log_transition`
      usa `log_audit_event(...)` con `actor=actor` y `module="convocatories"`.
      Eliminar el `try/except Exception: pass`.
- [x] `apps/applications/services/wizard_service.py::_log_submission`
      usa `log_audit_event(...)` con `actor=actor` y `module="applications"`.
      Eliminar el `try/except Exception: pass`.
- [x] `apps/audit/signals.py::audit_save_receiver` y
      `audit_delete_receiver` usan `log_audit_event(...)` con
      `actor=get_actor()` y `module=<audited model app label>`. Eliminar
      los `try/except Exception: pass`; en su lugar, log estructurado
      vía `apps.core.logging_config.logger.exception(...)`.
- [x] Verificación final: `grep -r "AuditEvent.objects.create" apps/`
      retorna 0 resultados.

## 5. Tighten AuditEventListView permission_classes

- [x] `apps/audit/views.py::AuditEventListView` y
      `AuditEventDetailView` cambian
      `permission_classes = [permissions.IsAuthenticated]` a
      `permission_classes = [IsAuditViewer]`.
- [x] Importar `IsAuditViewer` desde `apps.accounts.permissions`
      (ya existe en `apps/accounts/permissions.py:230-248`).
- [x] `AuditChainVerifyView` mantiene `IsAdminUser` (sólo
      verificación, no lectura general).

## 6. Tests (chain integrity, concurrency, signals auto-fire, view permissions)

- [x] Crear `apps/audit/tests/__init__.py` y `apps/audit/tests/conftest.py`
      con `pytest` conventions (fixtures `user`, `admin_user`,
      `aspirante_user`).
- [x] `apps/audit/tests/test_chain.py`:
  - [ ] Test que crea 3 eventos consecutivos vía `log_audit_event(...)`
        y verifica `current_hash[N] == sha256(previous_hash[N-1] +
        payload[N])` y `verify_chain()` retorna `is_valid=True`.
  - [ ] Test de hash determinístico: con la misma entrada
        `calculate_hash(...)` retorna el mismo hex.
- [x] `apps/audit/tests/test_concurrency.py`:
  - [ ] Lanza 2 hilos con `threading.Thread`, cada uno escribe N
        eventos dentro de `transaction.atomic`. Después verifica
        `verify_chain()` retorna `is_valid=True` y la cantidad de
        eventos es `2*N` sin colisiones de `current_hash` (índice
        único del modelo).
  - [ ] Si el runner de tests no soporta `TransactionTestCase`, usar
        `django.test.TransactionTestCase` con
        `serialized_rollback=True`.
- [x] `apps/audit/tests/test_signals.py`:
  - [ ] Mockear `actor` vía `actor_var.set(user)` antes de guardar un
        `Role`; verificar que se crea un `AuditEvent` con
        `actor=<mocked user>` y `previous_hash` correcto.
  - [ ] Guardar un `Estrato` (catalog de `apps.core.models`);
        verificar que se crea un `AuditEvent` con `module="core"` y
        `entity="estrato"`.
- [x] `apps/audit/tests/test_views_permissions.py`:
  - [ ] `R-ASPIRANTE` autenticado recibe `HTTP 403` en
        `GET /api/audit/events/`.
  - [ ] `R-ADMIN` autenticado recibe `HTTP 200`.
  - [ ] Usuario no autenticado recibe `HTTP 401` o `302` a login.

## 7. Verificación end-to-end

- [x] `python manage.py check` sin errores.
- [x] `python -m pytest apps/audit/ apps/legalization/ apps/accounts/
      apps/convocatories/ apps/applications/ -x --no-header -q` corre
      sin collection errors y los tests verdes se reportan.
- [x] `grep -r "AuditEvent.objects.create" apps/` retorna 0 matches.

## Pruebas

Archivos a crear en esta fase:

- `apps/audit/tests/__init__.py` (vacío o docstring).
- `apps/audit/tests/conftest.py` — fixtures pytest.
- `apps/audit/tests/test_chain.py` — integridad del hash chain.
- `apps/audit/tests/test_concurrency.py` — concurrencia con
  `threading` + `transaction.atomic`.
- `apps/audit/tests/test_signals.py` — signals automáticos.
- `apps/audit/tests/test_views_permissions.py` — R-ASPIRANTE recibe
  403.

Archivos a crear/modificar en `apps/`:

- `apps/audit/services.py` — agregar lock y docstring.
- `apps/audit/signals.py` — clases reales en `AUDIT_MODELS`, comparar
  `is`-equality, `actor=get_actor()`.
- `apps/audit/apps.py` — llamar `register_audit_signals()` desde
  `ready()`.
- `apps/audit/views.py` — `permission_classes = [IsAuditViewer]`.
- `apps/core/middleware.py` — setear `actor_var` desde
  `request.user`.
- `apps/core/logging_config.py` — agregar contextvar `actor_var`.
- `apps/legalization/signer.py` — usar `log_audit_event(...)`.
- `apps/accounts/services/notifications.py` — usar
  `log_audit_event(...)`.
- `apps/convocatories/services/convocatoria_service.py` — usar
  `log_audit_event(...)`.
- `apps/applications/services/wizard_service.py` — usar
  `log_audit_event(...)`.

Archivos NO a tocar (fuera del scope de CHG-801):

- `apps/treasury/services.py` (AUD-004 / AUD-005 → otra change).
- `apps/governance/services/listado.py` (AUD-020 → otra change).
- `apps/reporting/`, `apps/psychosocial/` (fuera del scope).