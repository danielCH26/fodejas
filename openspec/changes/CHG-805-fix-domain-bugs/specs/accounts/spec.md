# accounts — delta for CHG-805 (AUD-006, AUD-008)

## MODIFIED — § Single definition of `HasRole`

`apps/accounts/permissions.py` SHALL contain exactly one
`class HasRole(permissions.BasePermission):` definition. The
constructor SHALL accept `role_code=None` and the `has_permission`
method SHALL resolve the role check through the `UserRole` /
`Role.code` table (`request.user.user_roles.filter(role__code=...)`).

The legacy helpers `has_role`, `has_any_role`, `has_all_roles` that
were previously defined as instance methods on the duplicate
`HasRole` SHALL be expressed as **module-level functions** in the same
file (already present at `apps/accounts/permissions.py` lines 188+
in the pre-change file). The duplicate class definition SHALL be
removed; importing `HasRole` from `apps.accounts.permissions` SHALL
yield a class that supports the DRF permission-class protocol.

RATIONALE: a duplicate top-level class with the same name silently
shadows the first definition in Python; the first definition's
methods become unreachable. See `docs/audits/initial-audit.md` §3.3
AUD-006.

## MODIFIED — § Role checks in views and helpers SHALL go through the `Role` table

Any view, mixin, helper function or template tag that needs to check
whether a user holds a given role SHALL resolve that role through the
`Role.code` table — either by calling
`PermissionMixin._has_role(user, role_code)` from
`apps.accounts.permissions_mixin` or by calling the module-level
`has_role(user, role_code)` helper from `apps.accounts.permissions`.

The pattern `user.groups.filter(name="R-XXX").exists()` (Django
auth `Group` lookup keyed by role code) SHALL NOT be used for role
checks. Checks against Django's `Group` are still permitted for
distinguishing `is_staff` / `is_superuser` semantics and for
non-role-related authorization, but NEVER as the source of truth for
the `R-XXX` role catalog introduced in CHG-101.

The three sites identified by the audit SHALL be migrated:

- `apps/applications/views.py:has_revisor_role(user)` — use
  `has_role(user, "R-REVISOR")`.
- `apps/scoring/views.py:has_comite_role(user)` — use
  `has_role(user, "R-COMITE")`.
- `apps/scoring/views.py:RankingView.dispatch` — replace the inline
  `request.user.groups.filter(name="R-COORDINADOR").exists()` with
  `has_role(request.user, "R-COORDINADOR")`.

RATIONALE: the Django `Group` and the `Role` tables are loosely
coupled via `Role.group` FK but the views hard-code `R-XXX` strings
against the `Group.name` column. A rename of either side breaks the
view silently. Routing every check through the `Role.code` table
makes the relationship explicit and migrates cleanly. See
`docs/audits/initial-audit.md` §3.3 AUD-008 (and the
`extended-audit.md` verification that `apps/claims/views.py` already
follows this pattern).

## ADDED — § Coverage requirement

The accounts app SHALL host at least one test asserting that
`HasRole` from `apps.accounts.permissions` accepts a `role_code`
keyword argument and that exactly one class named `HasRole` is
defined in the module.
