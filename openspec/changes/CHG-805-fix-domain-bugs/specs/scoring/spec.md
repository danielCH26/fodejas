# scoring — delta for CHG-805 (AUD-007)

## MODIFIED — § Atomicity of `calcular_puntaje_total`

The scoring service `apps/scoring/services/scoring_service.py` function
`calcular_puntaje_total(solicitud, actor)` SHALL execute inside a
`@transaction.atomic` block. Within that atomic block, the `PuntajeTotal`
row SHALL be acquired via
`PuntajeTotal.objects.select_for_update().get_or_create(...)`
using `solicitud` as the natural key and `{"calculado_por": actor}` as
the create defaults.

The function SHALL propagate the open transaction to its callers (views
such as `apps/scoring/views.py:ScoringEvaluateView.post` and
`ScoringCalculateView.post`), so the row-level lock taken by
`select_for_update()` covers the entire read-modify-write of
`puntaje_socioeconomico`, `puntaje_academico`, `puntaje_excelencia`,
`puntaje_total` and `calculado_por`.

RATIONALE: two scorers clicking "save" on the same solicitud can race
the `get_or_create` and the subsequent `save()`, producing inconsistent
score breakdowns (e.g. `puntaje_total` computed against a stale
component). The combination of `transaction.atomic` and
`select_for_update()` is the canonical Django+PostgreSQL pattern for
this. See `docs/audits/initial-audit.md` §3.3 AUD-007 (reclassified
CRITICAL in `docs/audits/extended-audit.md` §5.2).

## ADDED — § Coverage requirement

The scoring app SHALL host at least one test exercising the atomic
contract: a second concurrent or interleaved `calcular_puntaje_total`
call against the same `Solicitud` SHALL NOT produce a `PuntajeTotal`
with `puntaje_total` outside the linear combination of its
`puntaje_socioeconomico`, `puntaje_academico` and `puntaje_excelencia`
components under the configured weights. The test SHALL be gated with
`pytest.mark.skipif` to skip on SQLite / non-Postgres backends where
`SELECT FOR UPDATE` semantics are not preserved.
