"""Signals for admin actions audit logging.

NOTE (CHG-801): The audit receivers for ``CustomUser``, ``Role``,
``UserRole`` and other audited models now live in
``apps.audit.signals``. The handlers that used to be defined here
were a pre-existing workaround while the canonical receivers in
``apps.audit.signals`` were broken (AUD-010). With CHG-801 the
canonical receivers fire correctly for every model listed in
``AUDIT_MODELS``, so the duplicates here would double-write every
audit event and corrupt the hash chain.

The module is preserved so that ``apps.accounts.apps.AccountsConfig
.ready()`` can still ``import .signals`` without raising
``ImportError``, but every concrete handler is removed.

If a future change needs to add signals that are NOT audit-related
(e.g. cache invalidation on role assignment), they belong in a
separate module — do NOT re-introduce audit receivers here.
"""
# Intentionally empty: see the docstring above for context.
# Previously this file contained ``log_user_change``,
# ``log_role_change``, ``log_user_role_change`` and
# ``log_user_role_delete`` which all called
# ``apps.audit.services.log_audit_event`` directly. With the
# CHG-801 fix to ``apps.audit.signals``, those handlers duplicate
# the canonical receivers and have been removed.