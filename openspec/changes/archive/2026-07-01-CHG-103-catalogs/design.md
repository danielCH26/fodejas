# Design: CHG-103-catalogs — Catálogos Paramétricos del Dominio (CAP-023)

## Technical Approach

Introduce a reusable **abstract base model** `CatalogoDominio` in `apps/core/models.py` and 10 concrete sibling models that materialize it as separate PostgreSQL tables. Seed values via a `RunPython` data migration (`0002_seed_catalogs.py`) using `get_or_create(codigo=...)` for idempotency. Expose reads through `apps/core/selectors.py` (one function per catalog) for downstream consumers (FUI CAP-003, scoring CAP-005). Register every model in `apps/core/admin.py` and wire audit (CAP-022) by adding the 10 models to `apps/audit/signals.py::AUDIT_MODELS`. This maps directly to proposal §1–§5 and honors `project.md §7.4` (rules are data, not code): master lists become queryable rows, not hard-coded `choices`, so `ConfiguracionConvocatoria` (CAP-024) can reference them by FK.

## Architecture Decisions

### Decision: Abstract base vs. single polymorphic table

| Option | Tradeoff | Decision |
|---|---|---|
| Abstract `CatalogoDominio` → 10 concrete tables | No shared table, per-table FK integrity, DRY fields | ✅ Chosen |
| One `Catalogo` table with `tipo` discriminator | One table, no FK constraints, app enforces validity | Rejected |
| `choices` per consuming model | No schema, scattered values, breaks CAP-024 | Rejected |

**Rationale**: FK constraints from `applications`/`scoring` to the right table give DB-level integrity and make CAP-024 reference real rows. `abstract=True` keeps fields DRY without a useless shared table (AC: "CatalogoDominio no se migra a tabla propia").

### Decision: PK type — BigAutoField int vs UUID for audit compatibility

| Option | Tradeoff | Decision |
|---|---|---|
| BigAutoField int PK + uuid5 conversion in audit receiver | Consistent with accounts/core, no schema churn | ✅ Chosen |
| UUID PK per catalog model | Aligns with `AuditEvent.entity_id` UUIDField | Rejected (inconsistent with rest of `apps/`) |
| Alter `AuditEvent.entity_id` to generic field | Touches archived CAP-022, out of scope | Rejected |

**Rationale**: `apps/audit/services.py::log_audit_event` does `uuid.UUID(str(entity_id))`, which crashes for int PKs. The catalog audit receiver computes `uuid.uuid5(NAMESPACE_OID, f"core.{model_name}.{pk}")` before calling the service — deterministic, replay-safe, leaves the audit schema untouched.

### Decision: Admin vs API exposure

| Option | Tradeoff | Decision |
|---|---|---|
| Django admin only (this phase) | CRUD for operators, no REST surface, matches R-ADMIN | ✅ Chosen |
| DRF read-only endpoint per catalog | Extra serializers/views, not required by CAP-003 yet | Rejected (proposal §Riesgos) |

### Decision: Seeding strategy — data migration vs fixtures

| Option | Tradeoff | Decision |
|---|---|---|
| `0002_seed_catalogs.py` RunPython + `get_or_create` | Idempotent, versioned with schema, runs on `migrate` | ✅ Chosen |
| `manage.py loaddata` JSON fixtures | Detached from schema, easy to forget on deploy | Rejected |
| Python seed script outside migrations | Not run by `migrate`, drift risk | Rejected |

**Rationale**: Data migration guarantees values exist after every `migrate` and supports adding values later without breaking prod (AC: "loaddata equivalente via migration"). `get_or_create(codigo=...)` makes re-runs safe.

## Data Flow

```
Seed (0002) ──get_or_create──→ 10 catalog tables (core_estrato, core_gruposisben, …)
                                  ▲
  admin (CRUD) ──post_save/post_delete──→ apps.audit.signals ──uuid5──→ AuditEvent
                                  ▲
  apps.core.selectors ──filter(activo=True)──→ consumers (FUI CAP-003, scoring CAP-005)
```

Admin edits flow through the same audit signal as everything else; selectors are the only sanctioned read path for business logic (AGENTS.md §6.6).

## File Changes

| File | Action | Description |
|---|---|---|
| `apps/core/models.py` | Create | `CatalogoDominio` abstract base + `ActivosManager` + 10 concrete models |
| `apps/core/admin.py` | Create | Base `CatalogoAdmin` + `@admin.register` for each model |
| `apps/core/selectors.py` | Create | `get_<catalog>_activos()` per catalog (10 functions) |
| `apps/core/migrations/__init__.py` | Create | Make app migratable |
| `apps/core/migrations/0001_initial.py` | Create | Schema for 10 tables |
| `apps/core/migrations/0002_seed_catalogs.py` | Create | Idempotent `RunPython` seed of proposal §2 table |
| `apps/core/tests/test_catalogs.py` | Create | Model fields, `activos()`, `__str__`, ordering, `codigo` unique |
| `apps/core/tests/test_selectors.py` | Create | Each selector returns only `activo=True`, ordered by `orden` |
| `apps/core/tests/test_seed_migration.py` | Create | Run `0002` on empty + pre-seeded DB → idempotent, exact values |
| `apps/core/tests/test_admin.py` | Create | AdminSite smoke: registration, `list_display`, filters, search |
| `apps/audit/signals.py` | Modify | Append 10 catalog models to `AUDIT_MODELS`; uuid5 int→UUID helper |
| `apps/core/README.md` | Create | How to add a catalog value (data migration, not admin-only) |

## Interfaces / Contracts

Abstract base (non-obvious pattern — dual manager so `objects` keeps all rows while `activos` filters):

```python
class ActivosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(activo=True)

class CatalogoDominio(models.Model):  # abstract = True
    codigo = models.SlugField(max_length=32, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.TextField(blank=True, default="")
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)
    metadatos = models.JSONField(default=dict, blank=True)
    objects = models.Manager()      # all rows
    activos = ActivosManager()      # activo=True only

    class Meta:
        abstract = True
        ordering = ["orden", "nombre"]
    def __str__(self): return self.nombre
```

Each concrete model: `class Estrato(CatalogoDominio): pass` with its own `Meta(verbose_name=…)` in Spanish (UI convention). Audit uuid5 conversion in `apps/audit/signals.py`:

```python
def _entity_id_for(instance):
    pk = instance.pk
    if isinstance(pk, uuid.UUID): return pk
    return uuid.uuid5(uuid.NAMESPACE_OID,
                      f"{instance._meta.app_label}.{instance._meta.model_name}.{pk}")
```

## Testing Strategy

| Layer | What | Approach |
|---|---|---|
| Unit | Field inheritance, `activos()` excludes inactive, `__str__`, default `orden`, `codigo` unique | `pytest` + `TestCase` in `test_catalogs.py` |
| Unit | Selectors return active rows in `orden` order | `test_selectors.py` with `factory_boy` |
| Integration | `0002` seeds exact §2 values; idempotent on re-run and on pre-seeded DB | call `migrate` forward twice in `test_seed_migration.py` |
| Integration | `post_save`/`post_delete` create `AuditEvent` rows for each catalog | reuse `apps/audit` test harness |
| Smoke | Admin registration, `list_display`, filters, search | `test_admin.py` against `AdminSite` |

Seed values are grounded in `project.md §11`: `NivelFormacion` and `ModalidadApoyo` map 1:1 to §11.4 (Art. 16 Decreto 0372/2025); `GrupoSisben`/`Etnia` to §11.1 req 2–3 & §11.3; `MunicipioIsla` to §11.5; `CausalTerminacionConvenio` to §11.6 (Art. 14). No PII — only administrative codes/names (AGENTS.md §6.1).

## Migration / Rollout

**Forward**: `manage.py migrate core` runs `0001` (schema) then `0002` (seed). Single PR to `develop`, branch `feat/catalogs/CHG-103` (proposal §Modo de Entrega). No downstream FKs exist yet — first change touching `apps/core`.

**Rollback**: `git revert` on `develop` → `manage.py migrate core zero` drops the 10 tables; audit signals auto-disconnect when models are removed (proposal §Plan de Rollback). `0002` reverse is a no-op (seed values die with the table).

**Feature flag**: not needed — additive, no behavior change for existing apps.

## Open Questions

- [ ] Should `metadatos` JSON be schema-validated per catalog now (e.g., `NivelFormacion.duracion_maxima_años`) or deferred to CAP-024 `ConfiguracionConvocatoria`? Proposal leaves it free-form.
- [ ] Confirm `CausalTerminacionConvenio` 6-value consolidation vs. literal §11.6 Art.14 7-cause list — design follows proposal table.
