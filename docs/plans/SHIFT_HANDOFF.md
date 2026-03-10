# Shift Handoff — 2026-03-10

## Current state
- Repo renamed and aligned to `pi-odoo-skill-manager`.
- Global install path works via `pipx` (`pyproject.toml` + `pi_odoo_skill_manager.py` entrypoint).
- `./scripts/smoke-test.sh` is deterministic (`.venv/bin/python`) and passes.
- Skill catalog is consolidated (`odoo-otto` unified skill).
- Naming/paths aligned to:
  - `.pi/skill-manager`
  - `.pi/skills/shared-skill-manager`
- No known local secret leakage in tracked files; hygiene checks active.

## Product direction (active)
- Human-first: calm keyboard TUI UX (otto-like language and sectioning).
- Agent-first: deterministic CLI (`--output json`, `--describe`, `--dry-run` where mutating).
- KISS: one install path (`pipx`), one obvious setup path.

## Immediate next steps
1. Extend agentic contract to remaining automation-relevant commands (`wizard`, `reset-project-path`, optionally `components` detail parity).
2. Continue TUI polish toward otto feel:
   - clearer status/footer semantics
   - tighter action feedback copy
   - reduced visual noise in panels
3. Add/refresh targeted tests for newly added JSON/dry-run command behavior.

## Useful commands
```bash
# local dev setup
./scripts/bootstrap.sh
./scripts/smoke-test.sh

# global command (local editable)
pipx install --editable .
pi-odoo-skill-manager --help

# contract checks
pi-odoo-skill-manager doctor --describe --output json
pi-odoo-skill-manager cleanup --dry-run --output json <PROJECT_REPO_PATH>
```
