# Work Package: odoo-migration-impact

Date: 2026-03-11
Status: queued

## Context
Needed for Odoo-heavy toolchains and likely shared value across `osmo` and `otto`.

## Goal
Provide fast impact visibility for model/schema/view changes before rollout.

## Scope (v0)
1. Detect changed models, fields, and views from git diff.
2. Flag likely migration/data-risk hotspots.
3. Suggest minimum required test scope.
4. Emit text + JSON outputs.

## Non-goals (v0)
- No automatic migration execution.
- No full semantic parser of all custom code paths.

## Output sketch
- `impact_summary`
- `risk_items[]` (code, severity, location, message)
- `recommended_tests[]`
- `next_steps[]`

## Candidate fit
- Good candidate for `otto` integration.
- Can be exposed in `osmo` as deterministic command and/or shared skill entry.
