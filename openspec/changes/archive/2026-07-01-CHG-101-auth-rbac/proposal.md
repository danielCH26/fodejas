# Proposal: CHG-101-auth-rbac — Authentication, Roles & Permissions (CAP-001)

## Intent

Foundational auth + RBAC layer required by every downstream capability (CAP-002..CAP-030 per `project.md` §8). Today `apps/accounts/` is empty and `AUTH_USER_MODEL` is unset, so the 13 roles in §7 cannot be enforced — blocking trazabilidad de actor under Ley 1581/2012 and CPACA.

## Scope

**In Scope** — custom `User(AbstractUser)` with `documento`, `email` unique, `telefono`, `fecha_nacimiento`; email as `USERNAME_FIELD`. 13 `Role` records seeded from §7 via data migration. `UserRole(user, role, convocation_scope nullable)` so one user can hold R-COORD globally and R-CT scoped to one convocatoria. `Permission(app_label, action, convocation_scope nullable)` + `RolePermission` M2M. JWT (`djangorestframework-simplejwt`): login, refresh, logout (blacklist), `/me`. Self-registration for aspirants with email verification (48h TTL); internal users created by R-ADMIN. Password reset via single-use token (24h TTL). `has_perm_for(perm, convocation)` helper in `selectors/`/`services/` only (AGENTS.md §6). `pytest` tests for role seed, JWT lifecycle, convocation-scoped perm, reset, lockout. Synthetic fixtures — no PII (AGENTS.md §1).

**Out of Scope** — OAuth/SSO (roadmap). 2FA/TOTP (pending user). Durable audit log (CAP-022 — emits signals only here). Multidioma (CAP-030). Concrete email/SMS providers. Integrations with OCCRE/SNIES/SISBÉN — forbidden (`project.md` §1.4, §8.1).

## Capabilities

- **New**: `auth-rbac` — User + 13 roles + JWT + convocation/stage permissions (covers CAP-001).
- **Modified**: None. CAP-001 is foundational.

## Approach

Hybrid model — Option D from `explore.md`: `User(AbstractUser)`, email login. `Role`/`Permission` are first-class models (not raw Django Groups) so convocation scoping is explicit; Groups retained for admin. JWT: access 15 min, refresh 7 days, blacklist via `rest_framework_simplejwt.token_blacklist`. Permission checks in `selectors/`/`services/`; views thin. PII masked via `apps/core/logging.py` (Ley 1581/2012).

## Affected Areas

| Area | Impact |
|------|--------|
| `apps/accounts/models.py` | New — User, Role, Permission, UserRole, RolePermission |
| `apps/accounts/{views,serializers,urls,admin}.py` | New |
| `apps/accounts/migrations/0001_initial.py` + `0002_seed_roles.py` | New |
| `config/settings.py` | Modified — `AUTH_USER_MODEL`, `REST_FRAMEWORK`, `SIMPLE_JWT` |
| `pyproject.toml` | Modified — add `djangorestframework-simplejwt[crypto]>=5.3` |
| `apps/audit/signals.py` | Modified — consume `user_logged_in`, `user_login_failed`, `user_registered` |
| `apps/core/logging.py` | Modified — PII masker |

## Risks

| Risk | Mitigation |
|------|------------|
| Migration on populated DB | DB empty; document `migrate accounts zero` |
| Perm-check perf | Cache `(user_id, convocation_id) → perms` in Redis 5 min |
| Reset blocks FUI | Self-service + R-COORD backdoor logged in audit |
| Email delivery fails | Dev console; prod Celery+retry; UI resend |
| Blacklist Redis outage | In-memory fallback + alert |
| Email enumeration `/register` | Always return 200; separate "if-exists" email |

## Rollback Plan

`git revert` on `develop` → `manage.py migrate accounts zero` → unset `AUTH_USER_MODEL` (feature-flagged) → drop SimpleJWT. CAP-001 ships before user-facing data → zero downstream state.

## Dependencies

`djangorestframework-simplejwt[crypto]>=5.3` (new). `apps/audit/` signal hook (CAP-022 scaffold). `apps/core/secrets.py` for `JWT_SIGNING_KEY`.

## Success Criteria

- [ ] `pytest apps/accounts/` green: role seed, JWT issue/refresh/blacklist, convocation perm, reset, lockout.
- [ ] `Role.objects.count() == 13`; codes match §7.
- [ ] `AUTH_USER_MODEL = "accounts.User"`; `manage.py check` clean.
- [ ] `POST /api/auth/login/` → 200 + token; `/me/` → 200 with token, 401 without.
- [ ] `has_perm_for("applications.add_application", convocation=X)` true only for R-ASPIRANTE/R-BENEF scoped to X.
- [ ] Zero PII in fixtures/commits/logs (grep gate).
- [ ] `ruff`, `black`, `pre-commit` clean.

## Assumptions Confirmed by User

1. ✅ Aspirante registration required BEFORE FUI (cuenta obligatoria).
2. ✅ Password policy: Estricta — min 8 chars, mayúsculas + números + símbolos requeridos, sin rotación forzada.
3. ✅ JWT: access 15 min, refresh 7 days, sliding, hard logout after 30 days idle.
4. ✅ 2FA deferred (fuera de alcance por ahora).
5. ✅ Permission granularity: Por etapa (rol, convocatoria, etapa, acción).