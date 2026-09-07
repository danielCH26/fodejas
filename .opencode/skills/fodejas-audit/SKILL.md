---
name: fodejas-audit
description: Audit the FODEJAS project — build a coverage matrix vs `roadmap.md` and surface prioritized defects in implemented changes. Use ONLY when the user asks to audit, validate against the roadmap, check project status vs planned capabilities, find bugs in what is already done, or run a periodic health check on the codebase.
license: MIT
metadata:
  author: fodejas
  domain: project-governance
---

# fodejas-audit

Trigger this skill when the user asks any of:

- "audit the project", "run an audit", "auditoría"
- "what is done vs the roadmap", "validate against the roadmap"
- "check project status", "status vs plan"
- "find bugs in what is implemented", "hunt for defects", "revisión general"
- "pre-release health check", "periodic audit"

Do **not** trigger this skill for: a single change's verification (use `openspec-verify-change`), a PR review (use the 4R review lenses), or a spec compliance question (use `openspec-verify-change` with the specific change).

## What this skill does

Delegates to the `fodejas-audit` sub-agent, which performs a **two-phase read-only audit**:

1. **Coverage** — cross-references `roadmap.md` against `openspec/changes/`, `openspec/specs/`, `apps/`, and `tests/` to produce a matrix of planned vs actual state per `CAP-NNN` / `CHG-NNN` / `INF-NNN`.
2. **Defects** — for every capability with code present, hunts for blockers (data loss, broken audit chain, monetary errors, wrong deadlines), criticals (race conditions, N+1, PII, missing transactions), warnings (logic in views, hardcoded constants, missing permissions), and suggestions (missing normative-deadline tests, brittle errors).

The sub-agent writes a full markdown report and returns a one-line summary.

## How to invoke

1. **Always delegate.** Launch the `fodejas-audit` sub-agent — never run the audit inline. This audit reads dozens of files and benefits from a fresh context.

2. **Pass optional scope to the sub-agent:**
   - If the user named specific changes (`audit CHG-204 and CHG-205`), pass them as the sub-agent's `change_scope`.
   - If the user wants the report in a specific path, pass it as `report_path`.
   - Otherwise omit both — the sub-agent defaults to "all non-archived changes" and `docs/audits/audit-<timestamp>.md`.

3. **Read the report, then summarize for the user:**
   - Surface the executive summary numbers.
   - Show the top 3 risks.
   - Link to the report file (do not paste it in full unless the user asks).
   - If the report contains any BLOCKER, **stop and ask the user** what to do next (fix now, file a change, or defer) before taking action.

4. **Do not modify the report.** The sub-agent is the sole author. If the user wants changes, run another audit or edit the report explicitly.

## Example delegation

```
task(
  subagent_type: "general",
  prompt: "Run a fodejas-audit with change_scope='CHG-204,CHG-205' and report_path='docs/audits/pre-release.md'. Return the JSON summary block only.",
  ...
)
```

(Use the actual `task` tool surface available in your runtime — the orchestrator will translate as needed.)

## Anti-patterns

- Do **not** edit the sub-agent's findings or rewrite its report. Treat the report as a deliverable artifact.
- Do **not** trigger this skill for speculative "is the code clean" questions. Use a focused 4R lens for that.
- Do **not** ask the sub-agent to fix anything. Fixes go through normal `sdd-new` / `sdd-apply` flows.
