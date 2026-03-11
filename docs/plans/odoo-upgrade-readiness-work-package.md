# Work Package: odoo-upgrade-readiness

Date: 2026-03-11
Status: queued

## Context
Upgrade prep is repetitive and risk-heavy; should be standardized for `osmo` and `otto` workflows.

## Goal
Assess upgrade readiness against a target Odoo version with actionable findings.

## Scope (v0)
1. Detect deprecated/risky usage patterns.
2. Highlight likely merge-conflict hotspots in overrides/customizations.
3. Check core operational prerequisites (tests, config, module states where possible).
4. Emit text + JSON with prioritized actions.

## Output sketch
- `target_version`
- `readiness_score`
- `findings[]` (code, severity, location, message)
- `recommended_fixes[]`
- `blocking_items[]`

## Non-goals (v0)
- No automated code rewrite.
- No guarantee of full upgrade compatibility.

## Candidate fit
- Strong fit for `otto` assistant workflows and release planning.
- Shared contract style should match current `osmo` deterministic CLI direction.
