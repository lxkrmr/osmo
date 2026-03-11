# osmo

Lean local helper for managing pi skills in Odoo projects.

## Naming

`osmo` = **O**doo **S**kill **M**anagement t**O**ol

The final `O` in `osmo` (from t**O**ol) is an easter egg aligned with the `octo` / `otto` naming style.

## Principles

- TUI-first DX for humans (clear, friendly, low-friction)
- CLI-first determinism for agents (`json`-friendly, scriptable, reliable)
- One clear setup path (KISS)
- Shared skills stay consistent across docs, manifest, and defaults
- Distribution standard for tools: `pipx`

## Release notes

- `docs/releases/v0.2.0.md`
- `docs/releases/RELEASE_CHECKLIST.md`

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
- `pipx` makes `osmo` available in your shell `PATH` everywhere, so humans and agents can call the same command consistently.
- `pipx` isolates the CLI in its own environment, preventing global Python package conflicts.
- `bootstrap.sh` keeps repo dependencies inside `.venv`, so installs do not leak into system Python.
- `direnv allow` auto-activates `.venv` whenever you enter the repo, including new terminals (no manual re-activation step).
- hooks + smoke provide deterministic quality gates before commits.

Update:
```bash
pipx upgrade osmo
```

Uninstall:
```bash
pipx uninstall osmo
```

### Daily workflow

```bash
cd /path/to/osmo
# direnv auto-activates .venv
./scripts/smoke-test.sh
osmo
```

If dependencies change (`requirements.txt` updates), rerun:

```bash
./scripts/bootstrap.sh
```

## Human + Agent workflow (same command surface)

Why this matters:
- Humans and agents should run the same executable: `osmo`.
- This avoids “works in one shell, fails in another” issues.
- It keeps automation deterministic.

Human-first (interactive):

```bash
osmo
```

Agent-first (deterministic CLI):

```bash
osmo wizard /path/to/odoo-project --dry-run --output json
osmo doctor /path/to/odoo-project --output json
osmo cleanup /path/to/odoo-project --dry-run --output json
osmo reset-project-path --dry-run --output json
osmo wizard --describe --output json
osmo doctor --describe --output json
```

## TUI-first usage

Run the skill manager without arguments:

```bash
osmo
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
- `c` — cleanup/uninstall osmo-managed project artifacts (with confirm)
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
osmo reset-project-path
```

## Doctor is actionable

Both doctor modes give guidance, not only status:

- what failed/warned
- what to do next
- concrete follow-up commands when relevant
- JSON mode includes `checks_structured[]` (`check_code`, `category`, `resource`, `severity`, ...)
- JSON mode includes `recommendations_structured[]` with `code`, `severity`, `message`, `next_command`

Use quick `x` for in-TUI guidance, and `X` when you want the full report.

## Command mode (secondary)

The TUI is primary. Command mode is agent-friendly for deterministic automation:

```bash
osmo --help
osmo help --output json
osmo ui [PROJECT_REPO_PATH]
osmo wizard [PROJECT_REPO_PATH]
osmo wizard [PROJECT_REPO_PATH] --dry-run --output json
osmo wizard --describe --output json
osmo doctor [PROJECT_REPO_PATH]
osmo doctor [PROJECT_REPO_PATH] --output json
osmo doctor --describe --output json
osmo cleanup [PROJECT_REPO_PATH]
osmo reset-project-path --dry-run --output json
osmo reset-project-path --describe --output json
```

### Contract scope (explicit)

Automation contract (JSON/describe/dry-run where mutating):
- `wizard`, `doctor`, `cleanup`, `components`, `enable-skill`, `disable-skill`, `reset-project-path`

Human-ops commands (intentionally outside automation contract):
- `ui`, `new-skill`, `up`, `db`, `shell`, `test`, `lint`

Stable contract spec:
- `docs/cli-contract.md`

You can inspect command scope machine-readably via:

```bash
osmo help --output json
```

Look for:
- `data.contract_version`
- `data.contract_spec`
- `data.details[].params[]`

## From your Odoo project

Use the global `osmo` command (installed via `pipx`):

```bash
osmo
```

## How installation works (important)

The skill manager installs shared skills into your project via **symlinks** (not file copies).

- shared skills symlink directory:
  - `<odoo-project>/.pi/skills/shared-osmo/<skill>` → `<skill-manager-root>/skills/<skill>`

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
- CLI contract behavior (`scripts/test-cli-contracts.sh`)
- golden JSON snapshots (`scripts/test-cli-golden.sh`)

## Local git hook (recommended)

Install once:

```bash
./scripts/install-git-hooks.sh
```

This enables a local `pre-commit` hook that runs the smoke test before each commit.
