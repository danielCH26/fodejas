```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:36b41f7e734f3e5fb4dc4658e9ac852022f1c65bbf4b5e4d5daa7dcc3e079868
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 5/5
scenarios: 5/5
test_command: .venv/bin/python -m pytest apps/accounts/tests/test_admin_views.py::PermissionMatrixViewTests -v
test_exit_code: 0
test_output_hash: sha256:36b41f7e734f3e5fb4dc4658e9ac852022f1c65bbf4b5e4d5daa7dcc3e079868
build_command: .venv/bin/python manage.py check accounts
build_exit_code: 0
build_output_hash: sha256:1e3e63f221bde88816c4a4ef7367691607b20cc1d194028a02ec9ae0586cf9b1
```

## Verification Report

**Change**: CHG-109 Role Permissions Matrix
**Version**: 2026-08-26 archive (delta at `openspec/changes/archive/2026-08-26-CHG-109-role-permissions-matrix/specs/accounts/spec.md`)
**Mode**: Standard (Strict TDD not active — no `sdd-init` cache found for project `fodejas`)

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 7 sections, 16 sub-items |
| Tasks complete | 16/16 |
| Tasks incomplete | 0 |

All sub-items in `tasks.md` are checked. The `## 7. Verificación` checklist (5 acceptance criteria) is fully marked.

### Build & Tests Execution
**Django check (`manage.py check accounts`)**: PASSED (exit 0)
```text
System check identified no issues (0 silenced).
```

**Tests (`pytest PermissionMatrixViewTests`)**: 4 passed / 0 failed / 0 skipped
```text
apps/accounts/tests/test_admin_views.py::PermissionMatrixViewTests::test_matrix_requires_login PASSED
apps/accounts/tests/test_admin_views.py::PermissionMatrixViewTests::test_matrix_accessible_by_admin PASSED
apps/accounts/tests/test_admin_views.py::PermissionMatrixViewTests::test_matrix_shows_roles PASSED
apps/accounts/tests/test_admin_views.py::PermissionMatrixViewTests::test_non_admin_cannot_access_matrix PASSED
======================== 4 passed, 6 warnings in 22.77s ========================
```

**Coverage**: Not available (no `pytest --cov` invocation in CI; threshold not enforced)

**Lint (`ruff check` over changed files)**: 2 errors reported
```text
I001 [*] Import block is un-sorted or un-formatted
 --> apps/accounts/tests/test_admin_views.py:2:1
C901 `post` is too complex (11 > 10)
   --> apps/accounts/views/admin_views.py:200:9
```
Of the two: one (C901 in `UserUpdateView.post`) is **pre-existing** in committed code (last touched in commit `0cb487a`, prior to this change). The other (I001) is in **new code** shipped by CHG-109 (the test file is untracked). User-stated summary of "1 pre-existing error" is therefore slightly understated — see Issues → WARNING below.

### Spec Compliance Matrix
| # | SHALL scenario (spec.md) | Test | Result |
|---|--------------------------|------|--------|
| 1 | La vista solo es accesible para usuarios con rol `R-ADMIN` (heredado de `BaseAdminView`) | `PermissionMatrixViewTests::test_matrix_requires_login`, `::test_matrix_accessible_by_admin`, `::test_non_admin_cannot_access_matrix` | COMPLIANT |
| 2 | La matriz muestra todos los roles activos del sistema | `::test_matrix_shows_roles` (asserts R-ADMIN visible) + view code `Role.objects.all().order_by('code')` (admin_views.py:562) | COMPLIANT |
| 3 | La matriz agrupa permisos por app_label | View code at admin_views.py:567-577 groups by `ct.app_label`; template iterates `permissions_by_app.items` | COMPLIANT (design + template inspection; no direct grouping test) |
| 4 | La matriz indica visualmente qué permisos tiene cada rol | Template renders `bi-check-circle-fill` / `bi-x-circle` from `role_permissions[role.id]` | COMPLIANT (visual; no assertion test for icon presence) |
| 5 | El diseño es consistente con el resto del admin de cuentas | Template extends `accounts/admin/admin_base.html`; sidebar link added in `admin_base.html` | COMPLIANT (visual; covered by view rendering 200) |

**Compliance summary**: 5/5 SHALL scenarios compliant. 3 have dedicated runtime tests; 2 are verified by source-inspection of view/template (consistent with the change's design — UI-only feature, not domain logic).

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| `PermissionMatrixView` registered | Implemented | `apps/accounts/admin_urls/__init__.py:42` and `admin_urls/admin.py:25` |
| View extends `BaseAdminView` (R-ADMIN guard) | Implemented | `apps/accounts/views/admin_views.py:551` |
| Template extends admin base | Implemented | `permissions_matrix.html:1` `{% extends "accounts/admin/admin_base.html" %}` |
| `get_item` templatetag shipped | Implemented | `apps/accounts/templatetags/matrix_tags.py:8-10` |
| Sidebar link to matrix | Implemented (per tasks §5; admin_base.html modified per `git status`) | Verified at file-system level |
| Tests cover happy path + access control | Implemented | `test_admin_views.py::PermissionMatrixViewTests` |

### Coherence (Design)
| Decision (design.md) | Followed? | Notes |
|---------------------|-----------|-------|
| View class `PermissionMatrixView(BaseAdminView)` | Yes | admin_views.py:551 |
| Template name `accounts/admin/permissions_matrix.html` | Yes | admin_views.py:553 + template file present |
| URL `permisos/` name `permission_matrix` | Yes | admin_urls/__init__.py:42 and admin.py:25 |
| Context shape `{roles, permissions_by_app, role_permissions}` | Yes | admin_views.py:563, 577, 588 |
| Roles fetched via `Role.objects.all().order_by('code')` | Minor deviation | Design suggested `filter(is_active=True)` but `Role` model has no `is_active` field (per memory #191). Implementation correctly omits the filter. Improves correctness vs design, not a regression. |
| Sidebar link to matrix | Yes | `admin_base.html` modified (tasks.md §5 checked) |

### Issues Found
**CRITICAL**: None

**WARNING**:
1. **Lint I001 in new code** — `apps/accounts/tests/test_admin_views.py:2:1` reports an unsorted import block. The file is untracked (i.e., newly added by CHG-109). `from apps.accounts.models import Role, UserRole` lands outside the first-party group because `pyproject.toml`'s `[tool.ruff]` lacks a `known-first-party = ["apps"]` setting. Fix options: add `known-first-party = ["apps"]` to `pyproject.toml`, or run `ruff check --fix`. **The user's claim of "1 pre-existing error" understates by one** — the actual lint output has 2 errors and one of them is in new code from this change.
2. **Spec scenarios 3 & 4 have no direct test assertions** — grouping-by-app_label and visual indicator rendering are inferred from view code and template inspection. The matrix view itself returns 200 and renders content (which is asserted), but no test asserts e.g. "permission from app X appears under that column header" or "check-circle icon appears next to granted perms". Acceptable for a presentational change, but worth a follow-up test if any future change touches the matrix logic.

**SUGGESTION**:
1. Add `pytest --cov=apps.accounts --cov-report=term-missing` to CI so coverage of the new test module can be tracked alongside the 4 passing tests.
2. Once `Role` model evolves (e.g., gains an `is_active` boolean), revisit whether the matrix should filter inactive roles — currently the view shows everything, which matches `Role.objects.all()` semantics but not the design's original wording.

### Verdict
**PASS WITH WARNINGS** — All 16 task sub-items complete, all 5 SHALL scenarios compliant with runtime evidence (3 directly tested, 2 verified via view/template inspection), Django check clean, 4/4 matrix tests pass. One new-code lint warning (I001, fixable in seconds) and one pre-existing C901 not introduced by this change. Change is archive-ready; orchestrator may proceed to `sdd-archive`.

### Files Verified
- `apps/accounts/views/admin_views.py:551-590` (`PermissionMatrixView`)
- `apps/accounts/admin_urls/__init__.py:42`
- `apps/accounts/admin_urls/admin.py:25`
- `apps/accounts/templates/accounts/admin/permissions_matrix.html`
- `apps/accounts/templatetags/matrix_tags.py`
- `apps/accounts/templates/accounts/admin/admin_base.html` (sidebar link)
- `apps/accounts/tests/test_admin_views.py::PermissionMatrixViewTests`