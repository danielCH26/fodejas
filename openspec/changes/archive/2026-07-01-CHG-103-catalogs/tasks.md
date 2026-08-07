# Tasks — CHG-103-catalogs

## Review Workload Forecast
- **Total estimated lines**: 580
- **400-line budget risk**: LOW (Testing phase at 300 lines is safe)
- **Critical path**: Data migration seed must be idempotent before testing

## 1. Foundation (80 lines)
- [x] Create abstract `CatalogoDominio` in `apps/core/models.py` (30 lines)
  - Fields: `codigo` (SlugField unique), `nombre`, `descripcion`, `orden`, `activo`, `metadatos`
  - Dual managers: `objects` (all) + `activos` (filter activo=True)
  - `__str__` returns `nombre`, default ordering by `orden`
- [x] Implement `ActivosManager` in `apps/core/models.py` (10 lines)
  - Custom queryset filtering `activo=True`
- [x] Generate `0001_initial.py` migration (40 lines)
  - Schema for 10 concrete tables (no abstract table)
  - Verify via `migrate --plan`

## 2. Core Implementation (190 lines)
- [x] Create 10 concrete models in `apps/core/models.py` (100 lines)
  - `Estrato`, `GrupoSisben`, `Etnia`, `MunicipioIsla`, `NivelFormacion`, `ModalidadApoyo`, `TipoIes`, `TipoDocumento`, `EstadoDocumento`, `CausalTerminacionConvenio`
  - Each inherits `CatalogoDominio`, sets `Meta.verbose_name`
- [x] Build admin interface in `apps/core/admin.py` (20 lines)
  - Base `CatalogoAdmin` with `list_display`, `list_filter`, `search_fields`
  - Register all 10 models with `@admin.register`
- [x] Implement selectors in `apps/core/selectors.py` (50 lines)
  - `get_<catalog>_activos()` per catalog (10 functions)
  - Filters: `activo=True`, orders by `orden`
- [x] Modify audit signals in `apps/audit/signals.py` (20 lines)
  - Add 10 models to `AUDIT_MODELS`
  - Implement `_entity_id_for` uuid5 conversion for int PKs

## 3. Testing (300 lines)
- [x] Unit tests for models in `apps/core/tests/test_catalogs.py` (100 lines)
  - Verify field inheritance, `activos()` manager, `__str__`, `codigo` uniqueness
  - Test default `orden` behavior
- [x] Unit tests for selectors in `apps/core/tests/test_selectors.py` (50 lines)
  - Confirm only `activo=True` rows returned, correct ordering
- [x] Integration test for seed migration in `apps/core/tests/test_seed_migration.py` (100 lines)
  - Run `0002` on empty DB → exact values from proposal §2
  - Re-run test → idempotency (no duplicate errors)
- [x] Admin smoke tests in `apps/core/tests/test_admin.py` (50 lines)
  - Verify registration, `list_display`, filters, search functionality

## 4. Cleanup (10 lines)
- [x] Create `apps/core/README.md` (10 lines)
  - Documentation: "How to add catalog values via data migration"
  - Warning: Never modify via admin in production
- [x] Final validation
  - [x] `ruff check .` and `black --check .` pass
  - [x] `pytest apps/core/` returns 100% green

## Implementation Order
1. Foundation → 2. Core → 3. Testing → 4. Cleanup

> **Why this order?**
> - Models must exist before migrations (Foundation before Core)
> - Data migration (`0002`) requires schema from `0001`
> - Audit signals depend on concrete models being defined
> - Testing phase validates all prior work
> - Documentation is last as it references implemented patterns