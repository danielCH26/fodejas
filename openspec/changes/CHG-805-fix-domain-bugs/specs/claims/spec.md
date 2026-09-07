# claims — delta for CHG-805 (AUD-009)

## MODIFIED — § `CanCreateApelacion` resolves to the existing helper

`apps/claims/permissions.py:CanCreateApelacion.has_object_permission`
SHALL resolve its appeal-eligibility check by importing
`validar_apelacion` from `apps.claims.services.apelaciones` and
calling `validar_apelacion(obj, request.user)`, which returns the
`(is_valid: bool, error_message: str | None)` tuple.

The previous reference to `can_apelar` (which does not exist in
`apps/claims.services.apelaciones`) SHALL NOT appear anywhere in
`apps/claims/permissions.py`. If in the future the team introduces a
semantically distinct helper, the rename SHALL be performed as a
dedicated change with explicit call-site updates — NOT a silent
import alias.

RATIONALE: the audit found the import `from
apps.claims.services.apelaciones import can_apelar` and the call
`can_apelar(obj, request.user)` in `CanCreateApelacion`. The module
defines `validar_apelacion`, `crear_apelacion`, `iniciar_analisis`,
`confirmar_apelacion`, `revocar_apelacion` and `_verify_ofijur_role`
— but NOT `can_apelar`. Any DRF view that wires this permission
class would raise `ImportError` on first use. See
`docs/audits/initial-audit.md` §3.3 AUD-009.

## ADDED — § Coverage requirement

The claims app SHALL host at least one test that imports
`CanCreateApelacion` from `apps.claims.permissions` and invokes
`has_object_permission` against a stub `obj`. The test SHALL NOT
require the database and SHALL FAIL on `ImportError`. Existence of
the class import path is itself the regression under test.
