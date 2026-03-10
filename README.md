# pi-odoo-skill-manager

Lean local helper for managing pi skills in Odoo projects.

## Principles

- TUI-first DX for humans (clear, friendly, low-friction)
- CLI-first determinism for agents (`json`-friendly, scriptable, reliable)
- One clear setup path (KISS)
- Shared skills stay consistent across docs, manifest, and defaults
- Distribution standard for tools: `pipx`

## UX inspirations

- `lazygit`
- `lazydocker`
- `k9s`
- `otto`

Target feel: keyboard-first, readable, calm defaults, strong feedback loops.

## Developer setup (one path)

```bash
./scripts/bootstrap.sh
./scripts/install-git-hooks.sh
./scripts/smoke-test.sh
```

## TUI-first usage

Run the skill manager without arguments:

```bash
./pi-odoo-skill-manager.py
```

This opens the interactive TUI (default experience).

Layout is stack-based for readability:
- Skills (top)
- Details (middle)
- Activity log (bottom, larger for easier output review)

### TUI keys

- `↑/↓` or `j/k` — move selection
- `Enter` / `Space` — toggle selected skill
- `e` — enable selected skill
- `d` — disable selected skill
- `s` — run quick setup
- `c` — cleanup/uninstall skill-manager artifacts (with confirm)
- `x` — quick doctor summary + top fix suggestions
- `X` — full doctor report in terminal
- `r` — refresh
- `q` — quit

## Project path behavior

The tool resolves your Odoo project path by:

1. explicit argument (if provided), or
2. saved default from `.envrc.local` (`ODOO_REPO_PATH`), or
3. interactive prompt.

You can clear saved path with:

```bash
./pi-odoo-skill-manager.py reset-project-path
```

## Doctor is actionable

Both doctor modes give guidance, not only status:

- what failed/warned
- what to do next
- concrete follow-up commands when relevant

Use quick `x` for in-TUI guidance, and `X` when you want the full report.

## Command mode (secondary)

The TUI is primary. Command mode is still available:

```bash
./pi-odoo-skill-manager.py --help
./pi-odoo-skill-manager.py ui [PROJECT_REPO_PATH]
./pi-odoo-skill-manager.py wizard [PROJECT_REPO_PATH]
./pi-odoo-skill-manager.py doctor [PROJECT_REPO_PATH]
./pi-odoo-skill-manager.py cleanup [PROJECT_REPO_PATH]
```

## From your Odoo project

After setup, use the project entrypoint:

```bash
./.pi/skill-manager
```

## How installation works (important)

The skill manager installs skills into your project via **symlinks** (not file copies).

- project entrypoint symlink:
  - `<odoo-project>/.pi/skill-manager` → `<skill-manager-root>/pi-odoo-skill-manager.py`
- shared skills symlink directory:
  - `<odoo-project>/.pi/skills/shared-skill-manager/<skill>` → `<skill-manager-root>/skills/<skill>`

Why this is useful:
- one source of truth in the skill manager repo
- instant skill updates across linked projects
- easy cleanup/uninstall

Local hygiene behavior:
- the tool can add `.pi/` to local git exclude (`.git/info/exclude`)
- this is local-only and not committed

## Included skills

Current shared skills in this skill manager:

- `dev-workbench`
- `local-db`
- `semantic-commit-message`
- `odoo-otto`
- `odoo-log-debug`
- `odoo-pr-review`
- `odoo-shell-debug`
- `odoo-ui-check`
- `skill-authoring`
- `web-lookup`

Browser JS helpers used by `odoo-ui-check` are in:

- `skills/browser-tools/browser-tools/`

## Smoke test

```bash
./scripts/smoke-test.sh
```

Smoke uses `.venv/bin/python` and checks:
- CLI help/guardrails
- skill metadata consistency (`skills/`, manifest, docs, defaults)

## Local git hook (recommended)

Install once:

```bash
./scripts/install-git-hooks.sh
```

This enables a local `pre-commit` hook that runs the smoke test before each commit.
