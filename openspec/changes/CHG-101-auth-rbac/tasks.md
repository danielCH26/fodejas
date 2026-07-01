# Tasks — CHG-101-auth-rbac (CAP-001)

## 1. Foundation
- [x] Create `CustomUser` model in `apps/accounts/models.py` extending `AbstractUser` with fields: `rol` (ForeignKey to Role), `convocatoria` (ForeignKey), and audit fields
- [x] Update `project/settings.py`: Set `AUTH_USER_MODEL = 'accounts.CustomUser'`, configure `SIMPLE_JWT` with 15min access token, 7d refresh token, and 30d logout
- [x] Add `djangorestframework-simplejwt` to `requirements.txt` and install dependencies
- [x] Implement password validator in `apps/accounts/validators.py` enforcing 8+ chars, uppercase, number, and symbol

## 2. Core
- [x] Define `Role` model in `apps/accounts/models.py` with 13 roles from project.md §7 (Administrador Sistema, Coordinador Académico, etc.)
- [x] Implement `Permission` model with fields: `role`, `convocatoria`, `etapa`, `acción` (CRUD permissions)
- [x] Configure JWT blacklist in `project/settings.py` and add `TokenObtainPairView` overrides
- [x] Register token endpoints in `apps/accounts/urls.py` (`token/`, `token/refresh/`, `token/logout/`)

## 3. Views
- [x] Build `LoginView` in `apps/accounts/views.py` returning JWT tokens and user role metadata
- [x] Create `RegisterView` with role assignment logic and email verification flow
- [x] Implement password reset suite (`PasswordResetRequestView`, `PasswordResetConfirmView`) with email templates
- [x] Develop role-based `DashboardView` showing convocatoria-specific actions in `apps/accounts/views.py`

## 4. Templates
- [x] Integrate Bootstrap 5 in `templates/base.html` with primary (#003366) and accent (#28A745) colors via CSS variables
- [x] Create login/register templates using Crispy Forms in `apps/accounts/templates/accounts/` with HTMX attributes
- [x] Design dashboard template with role-specific navigation and HTMX partials for dynamic content

## 5. Tests
- [x] Write unit tests for models in `apps/accounts/tests/test_models.py` (role assignments, permission checks)
- [x] Test JWT flows in `apps/accounts/tests/test_jwt.py` (token expiration, refresh, blacklist)
- [x] Implement integration tests for auth views in `apps/accounts/tests/test_views.py`
- [x] Validate password rules in `apps/accounts/tests/test_validators.py`

## Implementation Summary

**Commits applied:**
- `72f5b67` - feat(CAP-001): auth models, JWT config, password validator
- `fedb7b0` - feat(CAP-001): auth views and Bootstrap 5 templates
- `d91f929` - feat(CAP-001): auth tests for models, JWT, and views

**Test results:** 38 passed, 6 failed (test isolation issues)

## Review Workload Forecast
- Estimated changed lines: 670
- 400-line budget risk: High
- Chained PRs recommended: Yes
- Chain strategy: **stacked-to-main**
- Delivery strategy: single-pr (user overridden to chained)

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

## Work Units (Chained PRs)

| Unit | Goal | PR | Base |
|------|------|-----|------|
| 1 | Foundation + Core (Models, Settings, JWT) | PR #1 → develop | models + config |
| 2 | Views + Templates (Auth + UI) | PR #2 → PR #1 | views + templates |
| 3 | Tests | PR #3 → PR #2 | tests |

## Line Count Estimate
- **Foundation**: 85 lines
- **Core**: 110 lines
- **Views**: 120 lines
- **Templates**: 145 lines
- **Tests**: 210 lines
- **Total**: 670 lines

## Critical Notes
1. PRs follow **stacked-to-main** chain strategy
   - PR1: Foundation + Core (195 lines)
   - PR2: Views + Templates (265 lines)
   - PR3: Tests (210 lines)
2. All templates **must** use `crispy_form` tags with Bootstrap 5 layout
3. Role constants must match exact names from project.md §7
4. Password validator must reject common passwords (test against `django-common-passwords`)
5. JWT logout must invalidate refresh tokens via blacklist