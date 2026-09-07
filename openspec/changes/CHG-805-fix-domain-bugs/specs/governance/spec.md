# governance — delta for CHG-805 (AUD-005)

## MODIFIED — § Definitive listing state transition and PuntajeTotal field references

`apps/governance/services/listado.py:generar_listado_definitivo` SHALL
transition the related `Convocatory` to `Convocatory.Estado.DEFINITIVA`
(not the non-existent `RESULTADOS_DEFINITIVOS`). The detailed payload
assembled in `obtener_ranking_final` SHALL reference only the real
fields of `apps.scoring.models.PuntajeTotal`:
`puntaje_excelencia`, `puntaje_academico`, `puntaje_socioeconomico`
plus the aggregate `puntaje_total`. The legacy keys `puntaje_merito`
and `puntaje_residencia` SHALL NOT appear anywhere in the module.

## MODIFIED — § Failure handling for state transitions

The state-transition block inside `generar_listado_definitivo` SHALL
NOT silently swallow exceptions. The block SHALL catch
`AttributeError` and `ValueError` explicitly, emit a structured
WARNING log line identifying the convocatoria id, the attempted state
value and the exception class/message, and continue without
transitioning (so the operation stays idempotent). Any other exception
class SHALL propagate to the caller. The `try / except Exception: pass`
form SHALL NOT appear in this module.

RATIONALE: `apps/convocatories/models.py:Convocatory.Estado` declares
the estados in lines 41–48 with `DEFINITIVA` as the canonical state
for definitive results. The
`apps/scoring/models.py:PuntajeTotal` fields are
`puntaje_socioeconomico`, `puntaje_academico`, `puntaje_excelencia`
(`apps/scoring/models.py:90–117`). Silent exception swallowing
violates AGENTS.md §6 regla 5 (no skipping tests on admin-act
generation; observability failures of this kind are a CRITICAL class).
See `docs/audits/initial-audit.md` §3.2 AUD-005.

## ADDED — § Coverage requirement

The governance app SHALL host at least one test exercising
`generar_listado_definitivo` with synthetic `PuntajeTotal` rows that
populate the real field names. The test SHALL assert (a) no
`AttributeError` is raised, and (b) the convocatoria ends in the
`DEFINITIVA` state.
