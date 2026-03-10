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

## Requirements

- `python3` (with `venv`)
- `direnv`
- `pipx`

Install `direnv` with your OS package manager (examples):
- macOS (Homebrew): `brew install direnv`
- Ubuntu/Debian: `sudo apt-get update && sudo apt-get install -y direnv`
- Fedora: `sudo dnf install -y direnv`
- Arch: `sudo pacman -S direnv`
- Windows: `winget install direnv.direnv` (or `choco install direnv` / `scoop install direnv`)

If `pipx` is missing:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

## Recommended setup workflow (one way)

Run this exact sequence after cloning:

```bash
# 1) install the CLI globally (isolated via pipx)
pipx install --editable .

# 2) create repo-local venv and install deps
./scripts/bootstrap.sh

# 3) enable auto-activation of .venv for this repo
direnv allow

# 4) install local git hooks
./scripts/install-git-hooks.sh

# 5) verify setup
./scripts/smoke-test.sh
```

Why this is the recommended path:
- `pipx` makes `pi-odoo-skill-manager` available in your shell `PATH` everywhere, so humans and agents can call the same command consistently.
- `pipx` isolates the CLI in its own environment, preventing global Python package conflicts.
- `bootstrap.sh` keeps repo dependencies inside `.venv`, so installs do not leak into system Python.
- `direnv allow` auto-activates `.venv` whenever you enter the repo, including new terminals (no manual re-activation step).
- hooks + smoke provide deterministic quality gates before commits.

Update:
```bash
pipx upgrade pi-odoo-skill-manager
```

Uninstall:
```bash
pipx uninstall pi-odoo-skill-manager
```

### Daily workflow

```bash
cd /path/to/pi-odoo-skill-manager
# direnv auto-activates .venv
./scripts/smoke-test.sh
pi-odoo-skill-manager
```

If dependencies change (`requirements.txt` updates), rerun:

```bash
./scripts/bootstrap.sh
```

## Human + Agent workflow (same command surface)

Why this matters:
- Humans and agents should run the same executable: `pi-odoo-skill-manager`.
- This avoids “works in one shell, fails in another” issues.
- It keeps automation deterministic.

Human-first (interactive):

```bash
pi-odoo-skill-manager
```

Agent-first (deterministic CLI):

```bash
pi-odoo-skill-manager doctor /path/to/odoo-project --output json
pi-odoo-skill-manager cleanup /path/to/odoo-project --dry-run --output json
pi-odoo-skill-manager doctor --describe --output json
```

## TUI-first usage

Run the skill manager without arguments:

```bash
pi-odoo-skill-manager
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
pi-odoo-skill-manager reset-project-path
```

## Doctor is actionable

Both doctor modes give guidance, not only status:

- what failed/warned
- what to do next
- concrete follow-up commands when relevant

Use quick `x` for in-TUI guidance, and `X` when you want the full report.

## Command mode (secondary)

The TUI is primary. Command mode is agent-friendly for deterministic automation:

```bash
pi-odoo-skill-manager --help
pi-odoo-skill-manager ui [PROJECT_REPO_PATH]
pi-odoo-skill-manager wizard [PROJECT_REPO_PATH]
pi-odoo-skill-manager doctor [PROJECT_REPO_PATH]
pi-odoo-skill-manager doctor [PROJECT_REPO_PATH] --output json
pi-odoo-skill-manager doctor --describe --output json
pi-odoo-skill-manager cleanup [PROJECT_REPO_PATH]
```

## From your Odoo project

After setup, use the project entrypoint:

```bash
./.pi/skill-manager
```

## How installation works (important)

The skill manager installs skills into your project via **symlinks** (not file copies).

- project entrypoint symlink:
  - `<odoo-project>/.pi/skill-manager` → `<skill-manager-root>/pi_odoo_skill_manager.py`
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
