# convocatory-engine — delta for CHG-805 (AUD-011)

## MODIFIED — § Citation discipline for `NORMATIVA` entries

`apps/convocatories/domain/normativa.py:NORMATIVA` SHALL declare each
entry with a non-empty `articulo` string that cites the concrete
article and decree/ordenanza governing the plazo. The placeholder
literal `"Art. ... <decree>"` SHALL NOT appear in any entry of the
catalog.

The following entries are mandated for CHG-805; precise article
numbers are tentative until confirmed by the legal team:

- `beneficio_5_semestres` → `articulo: "Art. 11 Decreto 0372/2025"`.
- `beneficio_10_semestres` → `articulo: "Art. 11 Decreto 0372/2025"`.
- `tesoreria_5_dias` → `articulo: "Art. 2 Decreto 0072/2026"`.
  (The 5-working-day Tesorería window is governed by a separate
  decree per `docs/audits/initial-audit.md` §3.4 deadline audit.)
- `exoneracion_30_dias` → `articulo: "Art. 17 Decreto 0372/2025"`
  (sanction exoneration window per Decreto 0372/2025).

Each modified entry SHALL carry a comment of the form

```python
# TENTATIVE-CITATION: confirmar con equipo legal antes de deploy a producción
```

immediately above the entry, so a code reviewer can locate every
unconfirmed citation with one search. Legal confirmation SHALL be
tracked in a follow-up issue before the production deploy; this
spec does not block local/staging deploys.

RATIONALE: AGENTS.md §6 regla 4 prohibits inventing normativa.
Leaving the citation as a placeholder `"Art. ..."` is the same defect
in softened form. See `docs/audits/initial-audit.md` §3.4 AUD-011 and
the deadline audit in §4 (which tracks the two unverified plazo
buckets as separate issues).

## ADDED — § Coverage requirement

The convocatories app SHALL host at least one test that iterates the
`NORMATIVA` dict and asserts that no entry has `articulo` equal to
the substring `"Art. ..."` (literal-sweep — flags both `"Art. ..."`
and `"Art. ... Decreto …"` until they are replaced).
