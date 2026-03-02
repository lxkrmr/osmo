# pi-odoo-devkit

Lean local helper for managing pi skills in Odoo projects.

## TUI-first usage

Run the devkit without arguments:

```bash
./pi-odoo-devkit.py
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
- `c` — cleanup/uninstall devkit artifacts (with confirm)
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
./pi-odoo-devkit.py reset-project-path
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
./pi-odoo-devkit.py --help
./pi-odoo-devkit.py ui [PROJECT_REPO_PATH]
./pi-odoo-devkit.py wizard [PROJECT_REPO_PATH]
./pi-odoo-devkit.py doctor [PROJECT_REPO_PATH]
./pi-odoo-devkit.py cleanup [PROJECT_REPO_PATH]
```

## From your Odoo project

After setup, use the project entrypoint:

```bash
./.pi/devkit
```

## How installation works (important)

The devkit installs skills into your project via **symlinks** (not file copies).

- project entrypoint symlink:
  - `<odoo-project>/.pi/devkit` → `<devkit-root>/pi-odoo-devkit.py`
- shared skills symlink directory:
  - `<odoo-project>/.pi/skills/shared-devkit/<skill>` → `<devkit-root>/skills/<skill>`

Why this is useful:
- one source of truth in the devkit repo
- instant skill updates across linked projects
- easy cleanup/uninstall

Local hygiene behavior:
- the tool can add `.pi/` to local git exclude (`.git/info/exclude`)
- this is local-only and not committed

## Included skills

Current shared skills in this devkit:

- `dev-workbench`
- `local-db`
- `semantic-commit-message`
- `odoo-addon-lifecycle`
- `odoo-log-debug`
- `odoo-pr-review`
- `odoo-shell-debug`
- `odoo-translate`
- `odoo-ui-check`
- `skill-authoring`
- `web-lookup`

Browser JS helpers used by `odoo-ui-check` are in:

- `skills/browser-tools/browser-tools/`

## Smoke test

```bash
./scripts/smoke-test.sh
```

## Local git hook (recommended)

Install once:

```bash
./scripts/install-git-hooks.sh
```

This enables a local `pre-commit` hook that runs the smoke test before each commit.
