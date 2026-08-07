# Design: CHG-105-habeas-data — Habeas Data y Consentimientos (CAP-025)

## Technical Approach

Two models in `apps/accounts/` + `Festivo` catalog in `apps/core/`. Logic in `services/habeas_data.py` and `domain/{plazos,hashing}.py`; DRF views thin. Audit **service-driven** (AGENTS.md §7) via existing `log_audit_event` with new dotted actions. `NotificationPort` dispatcher defers real channels to CHG-106. Celery beat daily scan; minimal `config/celery.py` added (none exists today).

## Architecture Decisions

| Decision | Choice | Rejected | Rationale |
|---|---|---|---|
| Models location | `apps/accounts/` | New `apps/habeas/` | `roadmap.md` §5.1; User FK local |
| Consent versioning | Append-only + `revocado_en` (mirrors `ConvocatoriaVersion`) | In-place + history table | Immutable hash; tamper-detectable |
| Deadline calc | `domain/plazos.py` + `core.Festivo` | Hardcode/lib | Rule isolated; holidays as data |
| Celery setup | Add `config/celery.py`+beat here | Wait for CHG-106 | Daily scan needed; no app exists |
| Notifications | `NotificationPort` in services | Direct to missing app | Decouples from CHG-106 |
| Audit actions | Extend `ACTION_CHOICES` dotted, `action` 20→40 | New `event_type` field | Reuses hash chain; one migration |
| PII masking | `core/logging.py.mask_pii()` (CHG-103) | Inline | Centralized |

## Data Flow

Titular POSTs `/api/habeas-data/solicitudes/` → `HabeasDataViewSet` → `crear_solicitud()` computes `fecha_limite` (30 hábil), emits `habeas.created` (audit hash chain), notifies titular. Celery beat (daily 06:00) runs `habeas_expiry_check`: at día 25 hábil → notify R-ADMIN/R-COORD `habeas.expiring_soon`; `now > fecha_limite` & estado∈{radicada,en_tramite} → `estado=vencida`, `audit("habeas.expired")`, notify. R-ADMIN/R-COORD transition via admin/DRF action `transicionar()` → emits `habeas.resolved|rejected`, notify titular.

## Data Model

**`Consentimiento`** (`apps/accounts/models.py`): `titular` FK→CustomUser (PROTECT), `tipo` (TRATAMIENTO_DATOS|TRANSFERENCIA), `version_texto` TextField, `version_etiqueta` ("v3"), `hash_texto` CharField(64, indexed)=sha256(`version_texto`), `pdf_url` FileField→S3 (immutable: `AWS_S3_FILE_OVERWRITE=False`), `ip`+`user_agent`, `otorgado_en` auto, `revocado_en` nullable (set by new version). Indexes `(titular,tipo)`, `hash_texto`. Append-only — mirrors `ConvocatoriaVersion`.

**`SolicitudHabeasData`**: `Tipo` TextChoices (CONSULTA, RECTIFICACION, ACTUALIZACION, SUPRESION); `Estado` (RADICADA, EN_TRAMITE, RESUELTA, RECHAZADA, VENCIDA). `titular` FK PROTECT, `tipo`, `estado`, `descripcion`, `fecha_radicacion` auto, `fecha_limite` (30 días hábiles), `respuesta`/`motivo_rechazo` (validated on transition), `evidencia_url` FileField→S3, `resuelto_por` FK SET_NULL + `resuelto_en`, `suprimido_en` (soft-delete). Indexes `estado`, `fecha_limite`, `(titular,tipo)`.

**`Festivo`** (`apps/core/models.py`): `fecha` DateField unique, `nombre`. CAP-023 national catalog (Ley Emiliani 51/1983, Decreto 1175/2011).

## Service Layer

`apps/accounts/services/habeas_data.py` (transactional, audit+notify aware):
- `otorgar_consentimiento(titular,tipo,version_texto,ip,ua)` → store `consent_hash`, revoke prior active same-`tipo` (`revocado_en=now`), emit `consent.grant`.
- `verificar_integridad(consent)` → recompute; mismatch raises `HashMismatch` + `consent.tamper` (no save).
- `crear_solicitud(titular,tipo,descripcion)` → `fecha_limite=calcular_fecha_limite_habil(now,30)`, state `radicada`, `habeas.created`, notify.
- `transicionar(solicitud,actor,nuevo_estado,respuesta?,motivo?,evidencia?)` → enforces `radicada→en_tramite→{resuelta|rechazada}`, validates `respuesta`/`motivo`, acto-firme check for `supresion` (409), emits `habeas.resolved|rejected`, notify.
- `soft_delete_titular` → only from `supresion` resuelta sin acto firme; sets `suprimido_en` (20-yr retention, §5.5).

`domain/plazos.py`: `calcular_fecha_limite_habil(inicio,dias=30)` (skip Sat/Sun+`Festivo`), `dias_habiles_transcurridos(radicacion)`.
`services/notifications.py`: `NotificationPort.notify(user,event,payload)`; `NoopNotifier` default → CHG-106 binds real impl in `apps.py.ready()`.

## Admin Interface

`apps/accounts/admin.py` (empty today) registers `Consentimiento` (read-only list, masked email) and `SolicitudHabeasData` with `list_display`/`list_filter` (`estado`,`tipo`,`fecha_radicacion`,`fecha_limite`), `date_hierarchy=fecha_radicacion`, and `responder`/`rechazar` admin actions calling `transicionar`. Evidencia via `FileField`→S3. Restricted to R-ADMIN/R-COORD via `UserRole.role.code` check (CAP-001); 403 logged `permission_denied`.

## CAP-022 Audit Integration

Service-driven (never from view). `ACTION_CHOICES` += `consent.{grant,revoke,tamper}`, `habeas.{created,resolved,rejected,expiring_soon,expired,unauthorized}`, `permission_denied`; `action` `max_length` 20→40 (migration `audit/0003_*`). `changes` masked via `core/logging.py.mask_pii()` (CHG-103) before `log_audit_event`. Models **not** in `AUDIT_MODELS` (avoid duplicates; semantic events authoritative).

## CAP-019 Notifications Integration

`NotificationPort.notify()` at every transition with `(titular,event,payload_masked)`. `NoopNotifier` logs INFO until CHG-106 (tests assert the call). Events: `habeas.{created,resolved,rejected,expired,expiring_soon}` (last → R-ADMIN/R-COORD).

## Celery Task Design

New `config/celery.py` (`Celery("fodejas")`, `autodiscover_tasks(["apps.accounts"])`) + `apps/accounts/tasks.py`. `habeas_expiry_check` (shared_task): for each `SolicitudHabeasData` in `radicada|en_tramite`, compute `dias_habiles_transcurridos`; at 25 → `notify(R-ADMIN/R-COORD,"habeas.expiring_soon")`; if `now > fecha_limite` → `estado="vencida"`, save, `audit("habeas.expired")`, `notify(titular,"habeas.expired")`. Beat: daily 06:00 `America/Bogota` (`crontab(hour=6,minute=0)`). `apps/core/celery_metrics.py` already instruments `task_prerun/postrun`.

## Hash Computation (SHA-256)

`domain/hashing.py`: `consent_hash(version_texto)=sha256(version_texto.encode()).hexdigest()`, computed once at `otorgar_consentimiento` and stored in `hash_texto`. `verificar_integridad` recomputes + compares; mismatch → `HashMismatch` + `consent.tamper` audit (no row write). Signed PDF URL is append-only (`AWS_S3_FILE_OVERWRITE=False`), so the recorded text+hash are immutable.

## Holiday Calendar Integration

`core/models.Festivo` seeded by `core/migrations/0003_seed_festivos_2025_2026.py` (Ley Emiliani). `calcular_fecha_limite_habil` queries `Festivo.filter(fecha__range=...)` once per call. San Andrés uses national calendar (no departmental holidays). Re-seedable annually via data migration; no external API (gold rule #2).

## File Changes

| File | Action | Description |
|---|---|---|
| `apps/accounts/models.py` | Modify | Add `Consentimiento`, `SolicitudHabeasData` |
| `apps/accounts/migrations/0002_*.py` | Create | `Consentimiento` table |
| `apps/accounts/migrations/0003_*.py` | Create | `SolicitudHabeasData` table |
| `apps/accounts/services/habeas_data.py` | Create | Transitions, hash, soft-delete |
| `apps/accounts/domain/{plazos,hashing}.py` | Create | 30-day hábil + SHA-256 |
| `apps/accounts/services/notifications.py` | Create | `NotificationPort` + `NoopNotifier` |
| `apps/accounts/tasks.py` | Create | `habeas_expiry_check` |
| `apps/accounts/{views,serializers,admin,urls,apps}.py` | Modify | DRF + admin + `ready()` |
| `apps/audit/models.py` | Modify | `ACTION_CHOICES` += dotted; `action` 20→40 |
| `apps/audit/migrations/0003_*.py` | Create | Alter field |
| `apps/core/models.py` | Modify | Add `Festivo` |
| `apps/core/migrations/0003_*.py` | Create | Table + seed |
| `apps/core/logging.py` | Create | `mask_pii()` (CHG-103) |
| `config/celery.py` + `config/__init__.py` | Create/Modify | Celery app + beat |

> Proposal cited migrations `0006/0007` and `apps/core/logging.py`; only `0001` exists today → next numbers are `0002/0003`. `logging.py` is a CHG-103 dependency — consumed if it lands first.

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | `consent_hash`, `calcular_fecha_limite_habil` (festivo skip), transitions, acto-firme block | pure funcs + model tests |
| Unit | `otorgar_consentimiento` revokes prior; `verificar_integridad` raises `HashMismatch` | factories + `assertRaises` |
| Integration | POST `/api/habeas-data/solicitudes/` 401/403/201; admin role gate | `APIClient` + JWT |
| Integration | `habeas_expiry_check` día-25 + vencida | `celery_always_eager`, `freezegun` |
| Audit | `log_audit_event` dotted action; PII masked in `changes` | spy on service |

## Migration / Rollout

New accounts (×2) + audit field alter + `Festivo` table/seed. No data to migrate (CAP-025 ships before titulares). Rollback: `git revert` + reverse migrations. Beat entry disableable without revert. No feature flag needed.

## Open Questions

- [ ] CHG-103 `mask_pii` first? If not, add interim local masker here, refactor on merge.
- [ ] CHG-106 ships real `NotificationPort`, or keep `NoopNotifier` in MVP?
- [ ] `config/celery.py`+beat here, or dedicated bootstrap change (consumed by CAP-011/019)?
- [ ] Signed consent PDF: WeasyPrint here, or defer to CHG-202 (FUI)?
