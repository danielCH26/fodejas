"""Tests for the audit app (CAP-022 / CHG-801).

The audit chain must be structurally valid by construction — every
test in this package asserts against the chain invariants:

* SHA-256 hex of length 64
* ``current_hash[N] == sha256(payload[N], previous_hash[N-1])``
* ``verify_chain()`` returns ``is_valid=True`` for any sequence of
  successful ``log_audit_event(...)`` writes
* Concurrent writers serialize through ``SELECT ... FOR UPDATE``
* Signals attribute the actor from ``apps.core.logging_config``'s
  contextvar
* API endpoint denies ``R-ASPIRANTE`` and unauthenticated clients
"""