# Exploration: CHG-101-auth-rbac (CAP-001)

## Current State

The `apps/accounts/` app exists but is essentially empty:
- `models.py` — empty (no Custom User model)
- `views.py` — empty
- `apps.py` — basic Django AppConfig

**Django Setup:**
- Django 5.x with DRF (djangorestframework)
- **No SimpleJWT installed** (needs to be added to pyproject.toml)
- Using default Django User model (`django.contrib.auth.models.User`)
- Default AUTH_USER_MODEL not set in settings

**Roles defined in project.md (§7):**
- 13 roles: R-ASPIRANTE, R-BENEF, R-COORD, R-CT, R-JUNTA, R-PRES, R-SECEDU, R-TESOR, R-OFIJUR, R-CONTROL, R-CIUDA, R-AUDITOR, R-ADMIN
- 9 internal, 4 external
- RBAC requires granular permissions at **convocatory** and **stage** level

## Affected Areas

| File | Why Affected |
| ---- | ------------ |
| `apps/accounts/models.py` | Need Custom User model + Role/Permission models |
| `apps/accounts/views.py` | Auth endpoints (login, register, profile) |
| `pyproject.toml` | Missing SimpleJWT dependency |
| `config/settings.py` | Missing AUTH_USER_MODEL, REST_FRAMEWORK config, SimpleJWT settings |
| `apps/core/models.py` | May need to add Permission model for granular RBAC |
| All other apps | Will need @permission_required decorators or similar |

## Approaches

### Option A: Simple Django Groups + User Groups
- Use Django's built-in Groups and User.groups
- Add User to multiple Groups for roles
- Pros: Simple, built-in, minimal code
- Cons: No granular permissions at convocation/stage level without complex logic
- Effort: **Low**

### Option B: Custom User + Role Model + Django Guardian
- Custom User extending AbstractUser
- Role model with role_code, role_name, role_type (internal/external)
- UserProfile linking User to Role(s)
- Use django-guardian for object-level permissions
- Pros: Built-in support for row-level permissions, integrates with Django admin
- Cons: Additional dependency, more complex setup
- Effort: **Medium**

### Option C: Full Custom RBAC Implementation
- Custom User extending AbstractUser
- Separate Permission model with convocation_id, stage, action
- Role model with many-to-many to Permission
- Custom permission decorator checking convocation context
- Pros: Full control over granular permissions, matches project requirements
- Cons: More code to maintain, custom permission logic everywhere
- Effort: **High**

### Option D: Custom User + Role + Django Groups Hybrid (Recommended)
- Custom User extending AbstractUser
- Role model (Role = role_code + description)
- UserRole through model (user + role + convocation_scope optional)
- Use Django Groups for base permissions
- Add optional convocation-specific role via UserRole
- Pros: Balances simplicity with granular needs, uses Django patterns
- Cons: Slightly more complex than pure Groups
- Effort: **Medium**

## Recommendation

**Option D** — Custom User + Role + Django Groups Hybrid

### Justification:
1. **CAP-001 requires granular permissions** at convocation and stage level — Option A doesn't support this well
2. The 13 roles in project.md need explicit modeling, not just Groups
3. External users (aspirantes) need simplified auth flow vs internal users
4. Django-guardian adds complexity; custom convocation-scoped roles are more explicit

### Implementation sketch:
```
User (AbstractUser)
  └─ user_roles (M2M through UserRole)
       └─ Role (role_code, name, type)
            └─ permissions (M2M through RolePermission)
                 └─ Permission (app_label, model, action, convocation_scope nullable)
```

### JWT Strategy:
- Add `djangorestframework-simplejwt` to dependencies
- Access token: 15 minutes (short for security)
- Refresh token: 7 days (manageable for users)
- Blacklist refresh tokens on logout

### External Users (Aspirantes):
- Registration with email verification
- Limited to own profile + own applications
- No role initially — role assigned after selection (R-BENEF)
- R-CIUDA: public portal access (maybe anonymous or minimal)

## Risks

1. **Migration complexity**: Switching from default User to Custom User requires migration; test thoroughly
2. **Permission sprawl**: 13 roles × multiple stages × multiple convocations = potential permission explosion
3. **External user flow**: Aspirantes without login is unusual; need clear UX (anonymous FUI or account required)
4. **Performance**: Permission checks on every request; use caching
5. **PII exposure**: User data includes sensitive info; ensure proper field encryption and access controls (Ley 1581/2012)

## Ready for Proposal

**Yes**

The recommendation is clear: Option D with Custom User + Role + Django Groups hybrid approach. The proposal should include:
- SimpleJWT dependency addition
- Custom User model design
- Role and Permission models with convocation scoping
- JWT configuration in settings
- Auth endpoints (login, register, token refresh, logout, profile)
- Permission decorator/classes for convocation-stage granularity

**Next step**: Orchestrator should ask user to confirm this approach before proceeding to proposal.md.
