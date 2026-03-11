# Work Package: Cross-tool release guard CLI (osmo + otto)

Date: 2026-03-11
Status: queued (start tomorrow)

## Context
`osmo` and `otto` both need a deterministic release guard flow.
There are already ideas for additional tools that could reuse the same release checks.

## Goal
Design a small reusable release-check CLI that can be used by multiple internal tools.

## Draft direction
- Working name: `shipcheck` (placeholder).
- Repo-specific behavior via config file (e.g. `.releasecheck.toml`).
- Deterministic output + exit codes.
- JSON output for agent automation.

## Initial scope (v0)
1. Verify working tree clean.
2. Run configured quality gate command(s) (e.g. smoke).
3. Validate version + release notes + tag consistency.
4. Print/emit actionable next commands.

## Constraints
- Keep KISS: do not add unnecessary modes.
- Prefer one obvious path.
- Keep osmo command surface clean while evaluating extraction timing.

## Tomorrow kickoff
1. Define minimal config schema.
2. Define output contract (`text` + `json`).
3. Build small prototype against osmo + otto use-cases.
4. Decide: keep internal first vs immediate standalone package.
