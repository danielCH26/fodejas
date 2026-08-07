# Proposal: CHG-105-habeas-data — Habeas Data y Consentimientos (CAP-025)

## Intent

Cumplir **Ley 1581/2012** y **Decreto 1377/2013** desde Fase 1 (`roadmap.md` §5.1). Sin captura de consentimiento ni derechos ARCO (consulta, rectificación, actualización, supresión), el FODEJAS no puede inscribir titulares sin incumplir el deber de información — bloqueando CAP-002..CAP-030 que dependen de CAP-025 (`roadmap.md` §10).

## Scope

**In Scope**: `Consentimiento(titular, tipo, version_texto, fecha, hash_texto, ip, revocado_en)` y `SolicitudHabeasData(titular, tipo, estado, fecha_radicacion, fecha_limite, descripcion, respuesta, evidencia)`. Plazo **30 días hábiles** (Art. 14 Ley 1581/2012). Endpoint autenticado para titular; admin Django para R-ADMIN/R-COORD. Captura de consentimiento en FUI (CHG-202) con texto versionado + SHA-256. Notificación interna al titular en cada transición (CAP-019). Auditoría con PII enmascarada (CAP-022). Job Celery alerta vencimientos.

**Out of Scope**: integración con SIC; datos de menores; encargados externos; portal público ARCO (canal autenticado en MVP); supresión que afecte integridad de actos firmes (bloqueada, queda trazabilidad).

## Capabilities

- **New**: `habeas-data` — Consentimiento + Solicitudes ARCO + plazos + admin (covers CAP-025).
- **Modified**: None.

## Approach

Modelos en `apps/accounts/` (per `roadmap.md` §5.1). Plazos y transiciones en `apps/accounts/services/habeas_data.py`; vistas DRF delgadas. Cada cambio de política genera nueva versión de consentimiento; la anterior se conserva con `revocado_en`. Soft-delete en supresión para no romper auditoría (Ley 1581 — 20 años, `project.md` §5.5).

## Affected Areas

- `apps/accounts/models.py` — New: `Consentimiento`, `SolicitudHabeasData`.
- `apps/accounts/services/habeas_data.py` — New: plazos, transiciones, soft-delete.
- `apps/accounts/{views,serializers,admin}.py` — New: endpoints titular + admin.
- `apps/accounts/migrations/0006,0007` — New.
- `apps/audit/signals.py` — Modified: eventos `consent.*`, `habeas.*`.
- `apps/accounts/tasks.py` — New: Celery alerta vencimiento.

## Risks

| Risk | Mitigation |
|------|------------|
| Plazo 30d no respetado | Celery diario + alerta admin día 25 |
| Supresión borra auditoría | Soft-delete con `suprimido_en`; bitácora conserva |
| Revocación post-firma | Historial con `revocado_en`; no anula firma perfeccionada |
| PII en logs | `apps/core/logging.py` masker (CHG-103) |
| Texto sin trazabilidad | SHA-256 + URL inmutable del PDF en storage |

## Rollback Plan

`git revert` on `develop` → `migrate accounts zero` para los nuevos modelos. CAP-025 se entrega antes de Fase 2 (`CHG-202`) → sin titulares inscritos que perder.

## Dependencies

`apps/accounts/User` (CHG-101), `apps/audit/` (CHG-102), `apps/core/logging.py` (CHG-103), notificaciones CAP-019 (CHG-106). **Sin dependencias externas nuevas. Sin integración con SIC.**

## Success Criteria

- [ ] `pytest apps/accounts/tests/test_habeas_data.py` green: radicación, plazo, transición, rechazo, supresión, revocación.
- [ ] Plazo 30d hábiles enforced; alerta Celery día 25.
- [ ] Admin funcional: lista, filtra, responde, rechaza, carga evidencia.
- [ ] Endpoint titular autenticado (401 sin auth).
- [ ] Notificación al titular en cada transición; auditoría con PII enmascarada.
- [ ] Cero PII en fixtures/commits/logs; `ruff`/`black`/`isort`/`pre-commit` clean.