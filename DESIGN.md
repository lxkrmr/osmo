# DESIGN.md

Design rules and product decisions for `pi-odoo-skill-manager`.

## Goal
A lean skill manager for Odoo projects with:
- human-friendly TUI by default
- deterministic CLI for automation/agents
- one clear setup path (KISS)

## Product Principles
1. One path beats many paths.
2. Deterministic output beats implied behavior.
3. Shared command surface for humans and agents.
4. Remove backward-compat branches when they add noise.

## Setup Standard (One Path)
After clone:
1. `pipx install --editable .`
2. `./scripts/bootstrap.sh`
3. `direnv allow`
4. `./scripts/install-git-hooks.sh`
5. `./scripts/smoke-test.sh`

Rationale:
- `pipx` provides a stable global command without global package pollution.
- `.venv` keeps repo dependencies isolated.
- `direnv` auto-activates `.venv` on directory entry.
- smoke/hook checks keep behavior deterministic.

## CLI Contract Direction
- Human default: `pi-odoo-skill-manager` (TUI)
- Agent default: JSON-first commands
- Automation-relevant commands expose `--output json`
- Mutating commands should support `--dry-run`
- Doctor should return actionable recommendations

## Project Integration Model
- Project entrypoint: `.pi/skill-manager` symlink
- Shared skills under: `.pi/skills/shared-skill-manager/`
- Installation uses symlinks, not file copies

## Security & Privacy Policy
- Never commit secrets/tokens/real credentials.
- Use placeholders like `<odoo_login>`, `<odoo_password>`, `<db_name>`.
- Avoid personal machine paths in shared docs/examples.
- Keep generated local data out of git (`.venv/`, `.direnv/`, `node_modules/`).
- Run doctor before release/share:

```bash
pi-odoo-skill-manager doctor /path/to/odoo-project
```

## Non-Goals
- No multiple competing setup flows.
- No compatibility wrappers that hide the real entrypoint.
- No hidden magic that depends on one developer machine.

## Temporary Planning
Temporary work packages belong in:
- `docs/plans/`

They are disposable and should not become long-term architecture docs.
