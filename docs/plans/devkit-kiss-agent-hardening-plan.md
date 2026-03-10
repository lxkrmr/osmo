# Plan: transfer otto learnings to pi-odoo-devkit

Date: 2026-03-10
Status: agreed

## Goal
Make devkit workflows KISS, deterministic, and agent-friendly with one clear path for local execution.

## Decisions
- Keep one unified Odoo skill: `odoo-otto`.
- Prefer deterministic command usage in skills (`--output json`, `--dry-run` for mutating commands).
- Stabilize developer tooling so hooks/smoke use one known Python environment.

## Implementation
1. Add a single bootstrap path for local dev dependencies.
   - `scripts/bootstrap.sh`
   - `requirements.txt` (minimal)
2. Make smoke tests deterministic and explicit.
   - always run via `.venv/bin/python`
   - fail with actionable message if bootstrap not done
   - add metadata consistency checks
3. Add consistency checker for skill metadata.
   - skill folders vs `skills/manifest.json`
   - skill folders vs skill lists in `README.md` and `skills/README.md`
   - default skill recommendations must reference existing skills
4. Update docs to teach one path.
   - bootstrap -> install hooks -> smoke
   - explain KISS + deterministic skill contract

## Acceptance Criteria
- `./scripts/bootstrap.sh` prepares a working local environment.
- `./scripts/smoke-test.sh` runs without relying on global Python packages.
- stale skill references are caught automatically.
- docs reflect one clear setup path.
