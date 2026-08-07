# Design: CHG-104-convocatory-config — Modelo de Configuración de Convocatoria (Receta)

## Technical Approach

Treat the convocatoria recipe as a **hybrid document-relational model**: a single editable `ConfiguracionConvocatoria` (1→1 with `Convocatory`) holds the low-churn config as a JSON `payload` (requisitos, criterios de calificación, plazos normativos, reglas especiales), while high-query entities `Hito` and `Cupo` are normalized as FK-linked tables for direct SQL queries (e.g. "all cupos of Providencia"). An append-only `ConvocatoriaVersion` snapshots the full recipe (payload + hitos + cupos) on each publish, enabling revert without losing traceability (CAP-022). Business logic lives in `domain/validators.py` + `services/receta_service.py` + `selectors.py` — never in admin/views (AGENTS.md §6.6). Maps to proposal §1–§9 and **overrides §199** (Hito/Cupo now tables), **§248** (version history table), **§251** (editable admin) per the three confirmed decisions.

## Architecture Decisions

| # | Decision | Choice | Alternatives | Rationale |
|---|----------|--------|--------------|----------|
| 1 | Hito/Cupo storage | **Tables** (`Hito`, `Cupo` FK→`ConfiguracionConvocatoria`) | JSON arrays inside payload | Decision #1 confirmed; SQL queries on cupos/hitos (Providencia filter) without JSON unpacking; FK integrity to core catalogs (CAP-023) enforced at DB level |
| 2 | Version history | **Append-only `ConvocatoriaVersion`** snapshot table | In-place `version` int on config | Decision #2 confirmed; full revert; preserves "which recipe ruled" for CAP-022 audit; snapshot decouples history from live edits |
| 3 | Admin editability | **Editable `ConfiguracionConvocatoria` + inline `Hito`/`Cupo`** with `full_clean()` gate | Read-only JSON display | Decision #3 confirmed; graphical editing with validation; `ConvocatoriaVersion` stays read-only (history) |
| 4 | Stub preservation | **Extend** existing `Convocatory` stub (same table `convocatories_convocatory`) | Rename/replace | `accounts.Permission`/`UserRole` already FK to `convocatories.Convocatory` (string ref, CHG-101); extending keeps FKs valid |
| 5 | FK targets | `created_by`→`accounts.CustomUser`; cupos→`core.MunicipioIsla`/`ModalidadApoyo`/`NivelFormacion` | `User` | `CustomUser` is the real user model (CHG-101); core catalogs expose `activos` manager (CHG-103) |
| 6 | Audit wiring | Append 4 models to `AUDIT_MODELS` (string-path form like core) | New signal code | CHG-102 infra reused; CRUD auto-logged (§9) |

## Data Flow

```
Admin UI (editable) ──save──> ConfiguracionConvocatoria.full_clean()
      │                            │
      │                            ├─> validar_receta() [domain/validators.py]
      │                            │     ├─ jsonschema payload
      │                            │     ├─ sum(pesos)==100  (§11.3)
      │                            │     ├─ Hito/Cupo FKs active in core (CAP-023)
      │                            │     ├─ plazos vs nivel (§11.4)
      │                            │     └─ Providencia ref in normativa.py (§11.5)
      │                            ▼
      └──> ConfiguracionConvocatoria + Hito[] + Cupo[]  (live recipe)
                    │
      publicar_version() ─snapshot──> ConvocatoriaVersion (append-only)
                    │
      get_receta_vigente() ─────────> CAP-002 / CAP-004 / CAP-005 consumers
      revertir_version(v) <──────────  rollback from history
                    │
      audit signals ─────────────────> AuditEvent (CAP-022, hash chain)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `apps/convocatories/models.py` | Modify | Extend `Convocatory` (definitive fields + `EstadoConvocatoria` TextChoices + `activas()` manager); add `ConfiguracionConvocatoria` (1→1, JSON `payload`, `schema_version`), `Hito` (FK→config), `Cupo` (FK→config + core catalogs), `ConvocatoriaVersion` (append-only snapshot) |
| `apps/convocatories/domain/__init__.py` | Create | Package init |
| `apps/convocatories/domain/validators.py` | Create | `validar_receta(config)` — jsonschema + business rules; called from `full_clean()` |
| `apps/convocatories/domain/normativa.py` | Create | Immutable dict of normative refs (`Art. X Ordenanza 007/2025` → desc) |
| `apps/convocatories/services/__init__.py` | Create | Package init |
| `apps/convocatories/services/receta_service.py` | Create | `publicar_version()`, `revertir_version()`, `clonar_receta()` (alias to publish) |
| `apps/convocatories/selectors.py` | Create | `get_receta_vigente(convocatoria_id)` (prefetch hitos/cupos) |
| `apps/convocatories/migrations/__init__.py` | Create | Package init |
| `apps/convocatories/migrations/0001_initial.py` | Create | Schema for 4 models |
| `apps/convocatories/migrations/0002_seed_receta_excelencia_2026_1.py` | Create | Idempotent seed of §12 recipe (`get_or_create`) |
| `apps/convocatories/admin.py` | Modify | `ConvocatoryAdmin`, `ConfiguracionConvocatoriaAdmin` (editable + `TabularInline` `Hito`/`Cupo`), `ConvocatoriaVersionAdmin` (read-only) |
| `apps/convocatories/tests/` | Create | Unit (model+validator), service (publish/revert), selector, seed idempotency, audit smoke |
| `apps/convocatories/README.md` | Create | How to clone/edit a recipe |
| `apps/audit/signals.py` | Modify | Add 4 models to `AUDIT_MODELS` |
| `pyproject.toml` | Modify | Add `jsonschema>=4.21` |

## Interfaces / Contracts

```python
# models.py — key shapes (non-obvious decisions: extended stub, 1→1 editable, append-only version)
class Convocatory(models.Model):  # EXTENDED stub — same table, keeps accounts.* FKs valid
    class Estado(TextChoices):
        BORRADOR="borrador"; PUBLICADA="publicada"; EN_INSCRIPCION="en_inscripcion"
        EN_VERIFICACION="en_verificacion"; EN_CALIFICACION="en_calificacion"
        DEFINITIVA="definitiva"; CERRADA="cerrada"; CANCELADA="cancelada"
    codigo = models.SlugField(unique=True)
    # tipo, periodo, fechas, modalidad_apoyo FK (core), monto_semestre_smlmv, estado, created_by FK CustomUser
    activas = ActivasManager()  # filters ejecutable estados

class ConfiguracionConvocatoria(models.Model):  # 1→1, EDITABLE (decision #3)
    convocatoria = models.OneToOneField(Convocatory, CASCADE, related_name="config")
    schema_version = models.CharField(max_length=8, default="1.0.0")
    payload = models.JSONField(default=dict)  # requisitos, criterios, plazos, reglas_especiales
    def full_clean(self, *a, **k):
        validar_receta(self); super().full_clean(*a, **k)

class Hito(models.Model):  # TABLE (decision #1)
    config = models.ForeignKey(ConfiguracionConvocatoria, CASCADE, related_name="hitos")
    codigo = models.SlugField(max_length=32); orden; fecha_inicio; fecha_fin; responsable

class Cupo(models.Model):  # TABLE (decision #1) — DB-level FK to core catalogs
    config = models.ForeignKey(ConfiguracionConvocatoria, CASCADE, related_name="cupos")
    municipio = FK→core.MunicipioIsla; modalidad = FK→core.ModalidadApoyo
    nivel = FK→core.NivelFormacion; cantidad = PositiveInt; regla_especial = CharField(blank=True)

class ConvocatoriaVersion(models.Model):  # append-only HISTORY (decision #2)
    convocatoria = FK→Convocatory; version = PositiveInt
    schema_version; snapshot = JSONField  # serialized config+hitos+cupos
    created_by = FK→CustomUser; created_at; valida_hasta
    class Meta:
        unique_together = ("convocatoria", "version"); ordering = ["-version"]
```

## Testing Strategy

| Layer | What | Approach |
|-------|------|---------|
| Unit | `Convocatory` fields/manager/`__str__`, `codigo` unique constraint | pytest-django + factory_boy |
| Unit | `validar_receta` good/bad: pesos≠100 fail, inactive catalog FK fail, plazos §11.4 mismatch fail, Providencia ref not in `normativa.py` fail, unknown schema_version fail | table-driven |
| Unit | `Hito`/`Cupo` FK integrity to **active** core catalogs | create with inactive catalog → `ValidationError` |
| Service | `publicar_version` increments version, snapshot immutable, `AuditEvent` UPDATE created; `revertir_version` restores state; `clonar_receta` no-mutate | transactional tests |
| Selector | `get_receta_vigente` returns current config w/ hitos+cupos prefetched; ignores versions w/ past `valida_hasta` | — |
| Integration | Seed `0002` runs on clean DB and re-runs idempotently (`get_or_create`) | migrate + migrate again |
| Audit smoke | CRUD on all 4 models → `AuditEvent` rows, correct entity/module (CHG-102 infra) | — |
| Lint | `ruff check .`, `black --check .`, `isort --check .` clean | — |

## Migration / Rollout

- **Migration**: `0001_initial` creates 4 tables; reversible (no other apps FK into the new tables). `0002_seed` loads §12 recipe idempotently. No data migration from the stub (only `name` field, preserved by extending in place).
- **Reversibility**: `manage.py migrate convocatories zero` is safe — no downstream data (CAP-002..005 not yet running). `accounts` FKs to `Convocatory` keep resolving (same table, extended).
- **Rollback**: `git revert` on `develop` → `migrate convocatories zero` → remove 4 entries from `AUDIT_MODELS`. Export any in-use recipe payload to S3 (Ley 1581/2012, 20a retention) before revert if a piloto convocatoria exists.
- **Feature flag**: none — first materialization of CAP-024; no consumers yet.

## Open Questions

- [ ] Should `requisitos_minimos` / `criterios_calificacion` also normalize to tables in a follow-up CHG, or stay JSON? Out of scope here; revisit if payload exceeds ~20 top-level keys.
- [ ] Admin inline editing of `Hito`/`Cupo` via Django admin `TabularInline` vs. custom HTMX wizard — defer HTMX wizard to P1 (proposal §199).
